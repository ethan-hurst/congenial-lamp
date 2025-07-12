/**
 * Settings Page Component
 */
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import {
  HiUser,
  HiCog,
  HiCurrencyDollar,
  HiShield,
  HiBell,
  HiColorSwatch,
  HiKey,
  HiTrash
} from 'react-icons/hi';
import { FaGithub, FaGoogle } from 'react-icons/fa';
import toast from 'react-hot-toast';

import { Navbar } from '../components/Layout/Navbar';
import { useAuthStore } from '../stores/authStore';
import { useThemeStore } from '../stores/themeStore';
import { useEditorStore } from '../stores/editorStore';

interface ProfileFormData {
  fullName: string;
  email: string;
  username: string;
  bio: string;
  location: string;
  website: string;
}

interface PasswordFormData {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

export const SettingsPage: React.FC = () => {
  const { user, updateUser } = useAuthStore();
  const { isDarkMode, toggleTheme } = useThemeStore();
  const { fontSize, setFontSize, tabSize, setTabSize, wordWrap, toggleWordWrap } = useEditorStore();
  const [activeTab, setActiveTab] = useState('profile');

  const profileForm = useForm<ProfileFormData>({
    defaultValues: {
      fullName: user?.full_name || '',
      email: user?.email || '',
      username: user?.username || '',
      bio: '',
      location: '',
      website: ''
    }
  });

  const passwordForm = useForm<PasswordFormData>();

  const onProfileSubmit = async (data: ProfileFormData) => {
    try {
      // Update user profile
      updateUser({
        full_name: data.fullName,
        email: data.email,
        username: data.username
      });
      
      toast.success('Profile updated successfully');
    } catch (error) {
      toast.error('Failed to update profile');
    }
  };

  const onPasswordSubmit = async (data: PasswordFormData) => {
    if (data.newPassword !== data.confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    try {
      // Update password
      toast.success('Password updated successfully');
      passwordForm.reset();
    } catch (error) {
      toast.error('Failed to update password');
    }
  };

  const settingsTabs = [
    { id: 'profile', label: 'Profile', icon: HiUser },
    { id: 'account', label: 'Account', icon: HiCog },
    { id: 'billing', label: 'Billing', icon: HiCurrencyDollar },
    { id: 'security', label: 'Security', icon: HiShield },
    { id: 'notifications', label: 'Notifications', icon: HiBell },
    { id: 'appearance', label: 'Appearance', icon: HiColorSwatch },
    { id: 'editor', label: 'Editor', icon: HiKey },
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navbar />

      <div className="container mx-auto px-6 py-8">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">Settings</h1>

          <div className="flex flex-col lg:flex-row gap-8">
            {/* Sidebar */}
            <div className="lg:w-64 flex-shrink-0">
              <nav className="space-y-1">
                {settingsTabs.map(tab => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-lg transition ${
                        activeTab === tab.id
                          ? 'bg-primary-100 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
                          : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                      }`}
                    >
                      <Icon className="w-5 h-5 mr-3" />
                      {tab.label}
                    </button>
                  );
                })}
              </nav>
            </div>

            {/* Content */}
            <div className="flex-1">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
                {/* Profile Tab */}
                {activeTab === 'profile' && (
                  <div className="p-6">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
                      Profile Information
                    </h2>
                    
                    <form onSubmit={profileForm.handleSubmit(onProfileSubmit)} className="space-y-6">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Full Name
                          </label>
                          <input
                            {...profileForm.register('fullName')}
                            type="text"
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                          />
                        </div>
                        
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Username
                          </label>
                          <input
                            {...profileForm.register('username')}
                            type="text"
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                          />
                        </div>
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Email
                        </label>
                        <input
                          {...profileForm.register('email')}
                          type="email"
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Bio
                        </label>
                        <textarea
                          {...profileForm.register('bio')}
                          rows={3}
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                          placeholder="Tell us about yourself..."
                        />
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Location
                          </label>
                          <input
                            {...profileForm.register('location')}
                            type="text"
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                            placeholder="San Francisco, CA"
                          />
                        </div>
                        
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Website
                          </label>
                          <input
                            {...profileForm.register('website')}
                            type="url"
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                            placeholder="https://yoursite.com"
                          />
                        </div>
                      </div>
                      
                      <div className="flex justify-end">
                        <button
                          type="submit"
                          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
                        >
                          Save Changes
                        </button>
                      </div>
                    </form>
                  </div>
                )}

                {/* Security Tab */}
                {activeTab === 'security' && (
                  <div className="p-6">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
                      Security Settings
                    </h2>
                    
                    <form onSubmit={passwordForm.handleSubmit(onPasswordSubmit)} className="space-y-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Current Password
                        </label>
                        <input
                          {...passwordForm.register('currentPassword', { required: 'Current password is required' })}
                          type="password"
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          New Password
                        </label>
                        <input
                          {...passwordForm.register('newPassword', { required: 'New password is required', minLength: 8 })}
                          type="password"
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Confirm New Password
                        </label>
                        <input
                          {...passwordForm.register('confirmPassword', { required: 'Please confirm your password' })}
                          type="password"
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        />
                      </div>
                      
                      <div className="flex justify-end">
                        <button
                          type="submit"
                          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
                        >
                          Update Password
                        </button>
                      </div>
                    </form>
                  </div>
                )}

                {/* Appearance Tab */}
                {activeTab === 'appearance' && (
                  <div className="p-6">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
                      Appearance
                    </h2>
                    
                    <div className="space-y-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                          Theme
                        </label>
                        <div className="flex space-x-4">
                          <button
                            onClick={() => !isDarkMode && toggleTheme()}
                            className={`p-4 border-2 rounded-lg transition ${
                              !isDarkMode
                                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                                : 'border-gray-300 dark:border-gray-600 hover:border-primary-300'
                            }`}
                          >
                            <div className="w-16 h-12 bg-white border border-gray-300 rounded mb-2"></div>
                            <div className="text-sm font-medium">Light</div>
                          </button>
                          
                          <button
                            onClick={() => isDarkMode && toggleTheme()}
                            className={`p-4 border-2 rounded-lg transition ${
                              isDarkMode
                                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                                : 'border-gray-300 dark:border-gray-600 hover:border-primary-300'
                            }`}
                          >
                            <div className="w-16 h-12 bg-gray-800 border border-gray-600 rounded mb-2"></div>
                            <div className="text-sm font-medium">Dark</div>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Editor Tab */}
                {activeTab === 'editor' && (
                  <div className="p-6">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
                      Editor Preferences
                    </h2>
                    
                    <div className="space-y-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Font Size
                        </label>
                        <select
                          value={fontSize}
                          onChange={(e) => setFontSize(Number(e.target.value))}
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        >
                          {[10, 11, 12, 13, 14, 15, 16, 18, 20, 24].map(size => (
                            <option key={size} value={size}>
                              {size}px
                            </option>
                          ))}
                        </select>
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Tab Size
                        </label>
                        <select
                          value={tabSize}
                          onChange={(e) => setTabSize(Number(e.target.value))}
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        >
                          {[2, 4, 8].map(size => (
                            <option key={size} value={size}>
                              {size} spaces
                            </option>
                          ))}
                        </select>
                      </div>
                      
                      <div>
                        <label className="flex items-center space-x-3">
                          <input
                            type="checkbox"
                            checked={wordWrap}
                            onChange={toggleWordWrap}
                            className="w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded focus:ring-primary-500"
                          />
                          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            Word Wrap
                          </span>
                        </label>
                      </div>
                    </div>
                  </div>
                )}

                {/* Account Tab */}
                {activeTab === 'account' && (
                  <div className="p-6">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
                      Account Settings
                    </h2>
                    
                    <div className="space-y-8">
                      <div>
                        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-3">
                          Connected Accounts
                        </h3>
                        <div className="space-y-3">
                          <div className="flex items-center justify-between p-3 border border-gray-300 dark:border-gray-600 rounded-lg">
                            <div className="flex items-center space-x-3">
                              <FaGithub className="w-5 h-5" />
                              <span>GitHub</span>
                            </div>
                            <button className="text-sm text-primary-600 hover:text-primary-500">
                              Connect
                            </button>
                          </div>
                          
                          <div className="flex items-center justify-between p-3 border border-gray-300 dark:border-gray-600 rounded-lg">
                            <div className="flex items-center space-x-3">
                              <FaGoogle className="w-5 h-5" />
                              <span>Google</span>
                            </div>
                            <button className="text-sm text-primary-600 hover:text-primary-500">
                              Connect
                            </button>
                          </div>
                        </div>
                      </div>
                      
                      <div className="border-t border-gray-200 dark:border-gray-700 pt-8">
                        <h3 className="text-lg font-medium text-red-600 dark:text-red-400 mb-3">
                          Danger Zone
                        </h3>
                        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <h4 className="text-sm font-medium text-red-800 dark:text-red-200">
                                Delete Account
                              </h4>
                              <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                                Permanently delete your account and all data
                              </p>
                            </div>
                            <button className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition">
                              Delete
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};