import React, { useState } from 'react';
import { Search, Sparkles, X, Beaker, Globe, Languages, Building2, ArrowRight } from 'lucide-react';
import { Input } from '../common/Input';
import { Button } from '../common/Button';
import { SDSSearchRequest } from '../../types/sds';

interface SearchFormProps {
  onSearch: (payload: SDSSearchRequest) => void;
  isLoading: boolean;
}

const PRESETS: SDSSearchRequest[] = [
  {
    product_name: 'Acetone 99%',
    company_name: 'Sigma-Aldrich',
    country: 'United States',
    language: 'English',
  },
  {
    product_name: 'Isopropyl Alcohol 70%',
    company_name: 'Fisher Scientific',
    country: 'United States',
    language: 'English',
  },
  {
    product_name: 'Hydrochloric Acid 37%',
    company_name: 'Merck',
    country: 'Germany',
    language: 'English',
  },
  {
    product_name: 'Ethanol Absolute',
    company_name: 'VWR International',
    country: 'United States',
    language: 'English',
  },
];

export const SearchForm: React.FC<SearchFormProps> = ({ onSearch, isLoading }) => {
  const [productName, setProductName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [country, setCountry] = useState('United States');
  const [language, setLanguage] = useState('English');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!productName.trim()) {
      setError('Chemical product name is required.');
      return;
    }
    setError('');
    onSearch({
      product_name: productName.trim(),
      company_name: companyName.trim(),
      country: country.trim(),
      language: language.trim(),
    });
  };

  const handleApplyPreset = (preset: SDSSearchRequest) => {
    setProductName(preset.product_name);
    setCompanyName(preset.company_name || '');
    setCountry(preset.country || 'United States');
    setLanguage(preset.language || 'English');
    setError('');
  };

  const handleReset = () => {
    setProductName('');
    setCompanyName('');
    setCountry('United States');
    setLanguage('English');
    setError('');
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Primary Command Center Search Input */}
      <div className="space-y-2">
        <label className="block text-xs font-mono font-bold uppercase tracking-wider text-slate-300">
          Target Chemical Product <span className="text-cyan-400">*</span>
        </label>
        <div className="relative flex items-center group">
          <div className="absolute left-4 text-slate-500 group-focus-within:text-cyan-400 transition-colors pointer-events-none">
            <Beaker className="w-5 h-5" />
          </div>
          <input
            type="text"
            required
            disabled={isLoading}
            value={productName}
            onChange={(e) => {
              setProductName(e.target.value);
              if (error) setError('');
            }}
            placeholder="e.g. Acetone 99%, Isopropyl Alcohol, Methanol, Sulfuric Acid..."
            className="w-full bg-[#070A12] border border-white/[0.1] hover:border-white/[0.2] focus:border-cyan-400 focus:shadow-glow-cyan text-slate-100 placeholder:text-slate-500 text-sm md:text-base font-semibold rounded-2xl pl-12 pr-4 py-3.5 transition-all outline-none"
          />
        </div>
        {error && <p className="text-xs text-rose-400 font-medium pl-1">{error}</p>}
      </div>

      {/* Secondary Parameters Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Input
          label="Manufacturer / Supplier"
          placeholder="e.g. Sigma-Aldrich, Merck, Fisher..."
          value={companyName}
          onChange={(e) => setCompanyName(e.target.value)}
          disabled={isLoading}
          leftIcon={<Building2 className="w-4 h-4" />}
        />

        <Input
          label="Jurisdiction / Region"
          placeholder="e.g. United States, Germany, Global..."
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          disabled={isLoading}
          leftIcon={<Globe className="w-4 h-4" />}
        />

        <Input
          label="SDS Language"
          placeholder="e.g. English, German, French..."
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          disabled={isLoading}
          leftIcon={<Languages className="w-4 h-4" />}
        />
      </div>

      {/* Quick Example Chemicals */}
      <div className="space-y-2 pt-1">
        <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          <span>Quick Preset Shortcuts:</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((preset, idx) => (
            <button
              key={idx}
              type="button"
              disabled={isLoading}
              onClick={() => handleApplyPreset(preset)}
              className="text-xs px-3 py-1.5 rounded-xl bg-[#070A12] hover:bg-[#101828] text-slate-300 hover:text-cyan-300 border border-white/[0.08] hover:border-cyan-500/30 transition-all font-mono disabled:opacity-50 flex items-center gap-1.5"
            >
              <span>{preset.product_name}</span>
              <span className="text-slate-500">({preset.company_name})</span>
            </button>
          ))}
        </div>
      </div>

      {/* Action Footer */}
      <div className="flex items-center justify-between pt-4 border-t border-white/[0.06]">
        <div>
          {(productName || companyName) && !isLoading && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleReset}
              leftIcon={<X className="w-3.5 h-3.5" />}
            >
              Clear Console
            </Button>
          )}
        </div>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          isLoading={isLoading}
          rightIcon={<ArrowRight className="w-4 h-4" />}
          className="shadow-glow-cyan"
        >
          {isLoading ? 'Agent Verifying SDS...' : 'Execute SDS Verification'}
        </Button>
      </div>
    </form>
  );
};
