import { useState, useEffect } from 'react';
import { Settings as SettingsIcon, RefreshCw } from 'lucide-react';
import { endpoints } from '../lib/api';
import type { LLMProvider } from '../lib/api';

export function Settings() {
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [currentProvider, setCurrentProvider] = useState<string>('');
  const [currentModel, setCurrentModel] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState(false);

  useEffect(() => {
    loadProviders();
    loadCurrentProvider();
  }, []);

  const loadProviders = async () => {
    try {
      const response = await endpoints.listProviders();
      setProviders(response.data.providers);
    } catch (error) {
      console.error('Failed to load providers:', error);
    }
  };

  const loadCurrentProvider = async () => {
    try {
      const response = await endpoints.getCurrentProvider();
      setCurrentProvider(response.data.provider);
      setCurrentModel(response.data.model || '');
    } catch (error) {
      console.error('Failed to load current provider:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleProviderChange = async (providerType: string) => {
    setSwitching(true);
    try {
      await endpoints.setProvider(providerType);
      setCurrentProvider(providerType);
      // Clear model selection when provider changes
      setCurrentModel('');
      // Reload providers to get updated model list
      await loadProviders();
    } catch (error) {
      console.error('Failed to switch provider:', error);
      alert('Failed to switch provider. Please check if the provider is properly configured.');
    } finally {
      setSwitching(false);
    }
  };

  const selectedProvider = providers.find(p => p.type === currentProvider);
  const availableModels = selectedProvider?.models || [];

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
        <div className="flex items-center gap-3 mb-6">
          <SettingsIcon className="w-6 h-6 text-indigo-600" />
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
            LLM Provider Settings
          </h2>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        ) : (
          <div className="space-y-6">
            {/* Provider Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                LLM Provider
              </label>
              <select
                value={currentProvider}
                onChange={(e) => handleProviderChange(e.target.value)}
                disabled={switching}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Select a provider</option>
                {providers.map((provider) => (
                  <option key={provider.type} value={provider.type}>
                    {provider.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Model Selection */}
            {currentProvider && availableModels.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Model
                </label>
                <select
                  value={currentModel}
                  onChange={(e) => setCurrentModel(e.target.value)}
                  disabled={switching}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">Default model</option>
                  {availableModels.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name}
                      {model.context_window && ` (${model.context_window} tokens)`}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Provider Info */}
            {selectedProvider && (
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Provider Information
                </h3>
                <dl className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-gray-500 dark:text-gray-400">Type:</dt>
                    <dd className="text-gray-900 dark:text-gray-100 font-medium">
                      {selectedProvider.type}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500 dark:text-gray-400">Available Models:</dt>
                    <dd className="text-gray-900 dark:text-gray-100 font-medium">
                      {selectedProvider.models.length}
                    </dd>
                  </div>
                </dl>
              </div>
            )}

            {/* Status Messages */}
            {switching && (
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <div className="flex items-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-blue-600 dark:text-blue-400" />
                  <p className="text-sm text-blue-800 dark:text-blue-300">
                    Switching provider...
                  </p>
                </div>
              </div>
            )}

            {/* Configuration Notes */}
            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 space-y-2">
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Configuration Notes
              </h3>
              <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1 list-disc list-inside">
                <li>
                  <strong>Ollama:</strong> Requires Ollama to be running locally on port 11434
                </li>
                <li>
                  <strong>OpenAI:</strong> Requires OPENAI_API_KEY environment variable
                </li>
                <li>
                  <strong>Anthropic:</strong> Requires ANTHROPIC_API_KEY environment variable
                </li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}