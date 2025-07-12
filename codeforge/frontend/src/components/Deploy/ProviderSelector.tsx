/**
 * Provider Selector Component
 */
import React from 'react';
import {
  HiChevronDown,
  HiCheck,
  HiCloud,
  HiGlobeAlt,
  HiCpuChip,
  HiRocketLaunch
} from 'react-icons/hi2';

interface Provider {
  id: string;
  name: string;
  supports: string[];
  regions: string[];
}

interface ProviderSelectorProps {
  providers: Provider[];
  selectedProvider: string;
  onSelect: (providerId: string) => void;
  projectType: string;
}

// Provider logos/icons (in a real app, these would be actual logos)
const getProviderIcon = (providerId: string) => {
  switch (providerId) {
    case 'vercel':
      return '▲';
    case 'netlify':
      return '◆';
    case 'heroku':
      return '⬢';
    case 'aws_lambda':
      return '🅰';
    case 'google_cloud_run':
      return '🅶';
    case 'digital_ocean_apps':
      return '🌊';
    case 'railway':
      return '🚂';
    case 'render':
      return '🎨';
    case 'fly_io':
      return '🪰';
    case 'cloudflare_pages':
      return '☁️';
    default:
      return '☁️';
  }
};

const getProviderColor = (providerId: string) => {
  switch (providerId) {
    case 'vercel':
      return 'border-black dark:border-white bg-black dark:bg-white text-white dark:text-black';
    case 'netlify':
      return 'border-teal-500 bg-teal-500 text-white';
    case 'heroku':
      return 'border-purple-500 bg-purple-500 text-white';
    case 'aws_lambda':
      return 'border-orange-500 bg-orange-500 text-white';
    case 'google_cloud_run':
      return 'border-blue-500 bg-blue-500 text-white';
    case 'digital_ocean_apps':
      return 'border-blue-600 bg-blue-600 text-white';
    case 'railway':
      return 'border-gray-800 bg-gray-800 text-white';
    case 'render':
      return 'border-green-500 bg-green-500 text-white';
    case 'fly_io':
      return 'border-purple-600 bg-purple-600 text-white';
    case 'cloudflare_pages':
      return 'border-orange-400 bg-orange-400 text-white';
    default:
      return 'border-gray-500 bg-gray-500 text-white';
  }
};

const getProviderDescription = (providerId: string) => {
  switch (providerId) {
    case 'vercel':
      return 'Frontend cloud platform with edge network';
    case 'netlify':
      return 'Jamstack deployment with CDN and forms';
    case 'heroku':
      return 'Container-based cloud platform';
    case 'aws_lambda':
      return 'Serverless compute service';
    case 'google_cloud_run':
      return 'Fully managed container platform';
    case 'digital_ocean_apps':
      return 'Simple cloud hosting platform';
    case 'railway':
      return 'Modern deployment platform';
    case 'render':
      return 'Cloud platform for developers';
    case 'fly_io':
      return 'Global application platform';
    case 'cloudflare_pages':
      return 'JAMstack platform with edge computing';
    default:
      return 'Cloud deployment platform';
  }
};

export const ProviderSelector: React.FC<ProviderSelectorProps> = ({
  providers,
  selectedProvider,
  onSelect,
  projectType
}) => {
  const [isOpen, setIsOpen] = React.useState(false);
  
  const selectedProviderData = providers.find(p => p.id === selectedProvider);
  
  // Filter providers that support the current project type
  const compatibleProviders = providers.filter(provider =>
    provider.supports.includes(projectType) || provider.supports.length === 0
  );

  return (
    <div className="relative">
      {/* Selected Provider Display */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 hover:border-primary-500 transition"
      >
        <div className="flex items-center space-x-3">
          {selectedProviderData ? (
            <>
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold ${getProviderColor(selectedProvider)}`}>
                {getProviderIcon(selectedProvider)}
              </div>
              <div className="text-left">
                <div className="font-medium text-gray-900 dark:text-white">
                  {selectedProviderData.name}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {getProviderDescription(selectedProvider)}
                </div>
              </div>
            </>
          ) : (
            <>
              <HiCloud className="w-8 h-8 text-gray-400" />
              <div className="text-left">
                <div className="font-medium text-gray-900 dark:text-white">
                  Select Provider
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  Choose a deployment target
                </div>
              </div>
            </>
          )}
        </div>
        <HiChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg z-10 max-h-80 overflow-y-auto">
          {compatibleProviders.length === 0 ? (
            <div className="p-4 text-center text-gray-500 dark:text-gray-400">
              No compatible providers for {projectType.replace('_', ' ')}
            </div>
          ) : (
            <div className="py-2">
              {compatibleProviders.map((provider) => (
                <button
                  key={provider.id}
                  onClick={() => {
                    onSelect(provider.id);
                    setIsOpen(false);
                  }}
                  className="w-full flex items-center justify-between p-3 hover:bg-gray-50 dark:hover:bg-gray-600 transition"
                >
                  <div className="flex items-center space-x-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold ${getProviderColor(provider.id)}`}>
                      {getProviderIcon(provider.id)}
                    </div>
                    <div className="text-left">
                      <div className="font-medium text-gray-900 dark:text-white">
                        {provider.name}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {getProviderDescription(provider.id)}
                      </div>
                      
                      {/* Supported Features */}
                      <div className="flex items-center space-x-2 mt-1">
                        {provider.supports.includes('static_site') && (
                          <span className="inline-flex items-center space-x-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full">
                            <HiGlobeAlt className="w-3 h-3" />
                            <span>Static</span>
                          </span>
                        )}
                        {provider.supports.includes('spa') && (
                          <span className="inline-flex items-center space-x-1 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 px-2 py-0.5 rounded-full">
                            <HiRocketLaunch className="w-3 h-3" />
                            <span>SPA</span>
                          </span>
                        )}
                        {(provider.supports.includes('node_app') || provider.supports.includes('python_app')) && (
                          <span className="inline-flex items-center space-x-1 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 px-2 py-0.5 rounded-full">
                            <HiCpuChip className="w-3 h-3" />
                            <span>Server</span>
                          </span>
                        )}
                        {provider.supports.includes('serverless') && (
                          <span className="inline-flex items-center space-x-1 text-xs bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 px-2 py-0.5 rounded-full">
                            <span>⚡</span>
                            <span>Serverless</span>
                          </span>
                        )}
                      </div>
                      
                      {/* Regions */}
                      {provider.regions.length > 0 && (
                        <div className="text-xs text-gray-400 mt-1">
                          {provider.regions.length} region{provider.regions.length !== 1 ? 's' : ''} available
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {selectedProvider === provider.id && (
                    <HiCheck className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};