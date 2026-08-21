import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from src.schema import SDSValidationResult
from src.state import SDSState
from src.workflow import create_sds_graph, should_continue, extract_final_node, END

def test_sds_validation_result_schema():
    res = SDSValidationResult(
        status='EXACT MATCH',
        confidence=95,
        detailed_reasoning='Matches Sigma-Aldrich SDS for Acetone in English (US).',
        final_url='https://www.sigmaaldrich.com/US/en/sds/sial/179124'
    )
    assert res.status == 'EXACT MATCH'
    assert res.confidence == 95
    assert 'Sigma-Aldrich' in res.detailed_reasoning
    assert res.final_url.startswith('https://')

def test_sds_graph_compilation():
    graph = create_sds_graph()
    assert graph is not None
    node_keys = list(graph.nodes.keys())
    assert 'agent' in node_keys
    assert 'tools' in node_keys
    assert 'extract_final' in node_keys

def test_should_continue_no_tool_calls():
    state = {
        'messages': [AIMessage(content='I could not find the document.')],
        'row_data': {},
        'final_status': 'ERROR',
        'final_url': '',
        'confidence': 0,
        'detailed_reasoning': ''
    }
    decision = should_continue(state)
    assert decision == 'extract_final'

def test_should_continue_with_standard_tools():
    msg = AIMessage(
        content='',
        tool_calls=[{'name': 'search_duckduckgo', 'args': {'query': 'Acetone SDS'}, 'id': 'call_1'}]
    )
    state = {
        'messages': [msg],
        'row_data': {},
        'final_status': 'ERROR',
        'final_url': '',
        'confidence': 0,
        'detailed_reasoning': ''
    }
    decision = should_continue(state)
    assert decision == 'tools'

def test_should_continue_with_final_result_tool():
    msg = AIMessage(
        content='',
        tool_calls=[{
            'name': 'SDSValidationResult',
            'args': {
                'status': 'EXACT MATCH',
                'confidence': 90,
                'detailed_reasoning': 'Valid document found.',
                'final_url': 'https://www.fishersci.com/sds/123.pdf'
            },
            'id': 'call_final'
        }]
    )
    state = {
        'messages': [msg],
        'row_data': {},
        'final_status': '',
        'final_url': '',
        'confidence': 0,
        'detailed_reasoning': ''
    }
    decision = should_continue(state)
    assert decision == 'extract_final'

def test_extract_final_node_valid():
    msg = AIMessage(
        content='',
        tool_calls=[{
            'name': 'SDSValidationResult',
            'args': {
                'status': 'EXACT MATCH',
                'confidence': 90,
                'detailed_reasoning': 'Verified product match from Fisher Scientific.',
                'final_url': 'https://www.fishersci.com/sds/123.pdf'
            },
            'id': 'call_final'
        }]
    )
    state = {
        'messages': [msg],
        'row_data': {},
        'final_status': '',
        'final_url': '',
        'confidence': 0,
        'detailed_reasoning': ''
    }
    result = extract_final_node(state)
    assert result['final_status'] == 'EXACT MATCH'
    assert result['confidence'] == 90
    assert result['final_url'] == 'https://www.fishersci.com/sds/123.pdf'
    assert 'Fisher Scientific' in result['detailed_reasoning']

def test_extract_final_node_downgrade_placeholder_url():
    msg = AIMessage(
        content='',
        tool_calls=[{
            'name': 'SDSValidationResult',
            'args': {
                'status': 'EXACT MATCH',
                'confidence': 95,
                'detailed_reasoning': 'Found on example.',
                'final_url': 'https://example.com/sds.pdf'
            },
            'id': 'call_final'
        }]
    )
    state = {
        'messages': [msg],
        'row_data': {},
        'final_status': '',
        'final_url': '',
        'confidence': 0,
        'detailed_reasoning': ''
    }
    result = extract_final_node(state)
    assert result['final_status'] == 'NEEDS REVIEW'
    assert result['final_url'] == ''
    assert 'Downgraded: Rejected placeholder/invalid URL' in result['detailed_reasoning']

def test_extract_final_node_downgrade_low_confidence():
    msg = AIMessage(
        content='',
        tool_calls=[{
            'name': 'SDSValidationResult',
            'args': {
                'status': 'EXACT MATCH',
                'confidence': 40,
                'detailed_reasoning': 'Uncertain match.',
                'final_url': 'https://www.fishersci.com/sds/123.pdf'
            },
            'id': 'call_final'
        }]
    )
    state = {
        'messages': [msg],
        'row_data': {},
        'final_status': '',
        'final_url': '',
        'confidence': 0,
        'detailed_reasoning': ''
    }
    result = extract_final_node(state)
    assert result['final_status'] == 'NEEDS REVIEW'
    assert 'Downgraded: Low confidence' in result['detailed_reasoning']