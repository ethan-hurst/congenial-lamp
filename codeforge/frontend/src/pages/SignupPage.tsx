/**
 * Signup Page Component
 */
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { HiCode, HiEye, HiEyeOff, HiCheck } from 'react-icons/hi';
import { FaGithub, FaGoogle } from 'react-icons/fa';
import toast from 'react-hot-toast';

import { useAuthStore } from '../stores/authStore';
import { api } from '../services/api';

interface SignupFormData {
  email: string;
  username: string;
  password: string;
  confirmPassword: string;
  fullName: string;
  agreeToTerms: boolean;
  subscribeNewsletter: boolean;
}

export const SignupPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors }
  } = useForm<SignupFormData>();

  const password = watch('password');

  const onSubmit = async (data: SignupFormData) => {
    if (data.password !== data.confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    if (!data.agreeToTerms) {
      toast.error('Please agree to the terms and conditions');
      return;
    }

    setIsLoading(true);
    try {
      const response = await api.signup({
        email: data.email,
        username: data.username,
        password: data.password,
        full_name: data.fullName
      });
      
      // Store auth data
      login(response.user, response.tokens.access_token);
      
      toast.success('Account created successfully! Welcome to CodeForge!');
      navigate('/dashboard');
      
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Signup failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOAuthSignup = async (provider: 'github' | 'google') => {
    try {
      // Get OAuth URL
      const response = await fetch(`/api/v1/auth/oauth/${provider}/url`);
      const data = await response.json();
      
      // Store state for verification
      sessionStorage.setItem('oauth_state', data.state);
      
      // Redirect to OAuth provider
      window.location.href = data.auth_url;
      
    } catch (error) {
      toast.error(`Failed to initiate ${provider} signup`);
    }
  };

  const getPasswordStrength = (password: string) => {
    let score = 0;
    const checks = {
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /\d/.test(password),
      special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
    };

    Object.values(checks).forEach(check => {
      if (check) score++;
    });

    return { score, checks };
  };

  const passwordStrength = password ? getPasswordStrength(password) : { score: 0, checks: {} };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        {/* Logo */}
        <div className="flex justify-center">
          <Link to="/" className="flex items-center space-x-2">
            <HiCode className="w-10 h-10 text-primary-600 dark:text-primary-400" />
            <span className="text-3xl font-bold text-gray-900 dark:text-white">CodeForge</span>
          </Link>
        </div>
        
        <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900 dark:text-white">
          Create your account
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
          Already have an account?{' '}
          <Link
            to="/login"
            className="font-medium text-primary-600 hover:text-primary-500 dark:text-primary-400"
          >
            Sign in here
          </Link>
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white dark:bg-gray-800 py-8 px-4 shadow sm:rounded-lg sm:px-10">
          {/* Benefits */}
          <div className="mb-6 p-4 bg-primary-50 dark:bg-primary-900/20 rounded-lg">
            <h3 className="text-sm font-medium text-primary-900 dark:text-primary-100 mb-2">
              Start with 100 free credits:
            </h3>
            <ul className="text-xs text-primary-700 dark:text-primary-300 space-y-1">
              <li className="flex items-center">
                <HiCheck className="w-3 h-3 mr-1" />
                Unlimited projects (vs Replit's 3)
              </li>
              <li className="flex items-center">
                <HiCheck className="w-3 h-3 mr-1" />
                Any IDE support
              </li>
              <li className="flex items-center">
                <HiCheck className="w-3 h-3 mr-1" />
                Instant container starts
              </li>
            </ul>
          </div>

          {/* OAuth Buttons */}
          <div className="space-y-3">
            <button
              onClick={() => handleOAuthSignup('github')}
              className="w-full flex justify-center items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 transition"
            >
              <FaGithub className="w-5 h-5 mr-2" />
              Sign up with GitHub
            </button>
            
            <button
              onClick={() => handleOAuthSignup('google')}
              className="w-full flex justify-center items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 transition"
            >
              <FaGoogle className="w-5 h-5 mr-2" />
              Sign up with Google
            </button>
          </div>

          {/* Divider */}
          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300 dark:border-gray-600" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                  Or sign up with email
                </span>
              </div>
            </div>
          </div>

          {/* Signup Form */}
          <form className="mt-6 space-y-6" onSubmit={handleSubmit(onSubmit)}>
            {/* Full Name */}
            <div>
              <label htmlFor="fullName" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Full name
              </label>
              <div className="mt-1">
                <input
                  {...register('fullName', {
                    required: 'Full name is required'
                  })}
                  type="text"
                  autoComplete="name"
                  className="appearance-none block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="John Doe"
                />
                {errors.fullName && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.fullName.message}</p>
                )}
              </div>
            </div>

            {/* Email */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Email address
              </label>
              <div className="mt-1">
                <input
                  {...register('email', {
                    required: 'Email is required',
                    pattern: {
                      value: /^\S+@\S+$/i,
                      message: 'Invalid email address'
                    }
                  })}
                  type="email"
                  autoComplete="email"
                  className="appearance-none block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="you@example.com"
                />
                {errors.email && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.email.message}</p>
                )}
              </div>
            </div>

            {/* Username */}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Username
              </label>
              <div className="mt-1">
                <input
                  {...register('username', {
                    required: 'Username is required',
                    minLength: {
                      value: 3,
                      message: 'Username must be at least 3 characters'
                    },
                    pattern: {
                      value: /^[a-zA-Z0-9_-]+$/,
                      message: 'Username can only contain letters, numbers, hyphens, and underscores'
                    }
                  })}
                  type="text"
                  autoComplete="username"
                  className="appearance-none block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="johndoe"
                />
                {errors.username && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.username.message}</p>
                )}
              </div>
            </div>

            {/* Password */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Password
              </label>
              <div className="mt-1 relative">
                <input
                  {...register('password', {
                    required: 'Password is required',
                    minLength: {
                      value: 8,
                      message: 'Password must be at least 8 characters'
                    }
                  })}
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  className="appearance-none block w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-md placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="Create a strong password"
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <HiEyeOff className="h-5 w-5 text-gray-400" />
                  ) : (
                    <HiEye className="h-5 w-5 text-gray-400" />
                  )}
                </button>
              </div>
              
              {/* Password Strength */}
              {password && (
                <div className="mt-2">
                  <div className="flex space-x-1">
                    {[1, 2, 3, 4, 5].map(level => (
                      <div
                        key={level}
                        className={`h-1 flex-1 rounded ${
                          passwordStrength.score >= level
                            ? passwordStrength.score <= 2
                              ? 'bg-red-500'
                              : passwordStrength.score <= 3
                              ? 'bg-yellow-500'
                              : 'bg-green-500'
                            : 'bg-gray-200 dark:bg-gray-600'
                        }`}
                      />
                    ))}
                  </div>
                  <div className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                    <div className="grid grid-cols-2 gap-1">
                      <span className={passwordStrength.checks.length ? 'text-green-600 dark:text-green-400' : ''}>
                        8+ characters
                      </span>
                      <span className={passwordStrength.checks.uppercase ? 'text-green-600 dark:text-green-400' : ''}>
                        Uppercase
                      </span>
                      <span className={passwordStrength.checks.lowercase ? 'text-green-600 dark:text-green-400' : ''}>
                        Lowercase
                      </span>
                      <span className={passwordStrength.checks.number ? 'text-green-600 dark:text-green-400' : ''}>
                        Number
                      </span>
                    </div>
                  </div>
                </div>
              )}
              
              {errors.password && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.password.message}</p>
              )}
            </div>

            {/* Confirm Password */}
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Confirm password
              </label>
              <div className="mt-1 relative">
                <input
                  {...register('confirmPassword', {
                    required: 'Please confirm your password'
                  })}
                  type={showConfirmPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  className="appearance-none block w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-md placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="Confirm your password"
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                >
                  {showConfirmPassword ? (
                    <HiEyeOff className="h-5 w-5 text-gray-400" />
                  ) : (
                    <HiEye className="h-5 w-5 text-gray-400" />
                  )}
                </button>
                {errors.confirmPassword && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.confirmPassword.message}</p>
                )}
              </div>
            </div>

            {/* Terms and Newsletter */}
            <div className="space-y-3">
              <div className="flex items-start">
                <input
                  {...register('agreeToTerms', {
                    required: 'You must agree to the terms'
                  })}
                  id="agree-terms"
                  type="checkbox"
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 dark:border-gray-600 rounded mt-0.5"
                />
                <label htmlFor="agree-terms" className="ml-2 block text-sm text-gray-900 dark:text-gray-300">
                  I agree to the{' '}
                  <a href="#" className="text-primary-600 hover:text-primary-500 dark:text-primary-400">
                    Terms of Service
                  </a>{' '}
                  and{' '}
                  <a href="#" className="text-primary-600 hover:text-primary-500 dark:text-primary-400">
                    Privacy Policy
                  </a>
                </label>
              </div>
              
              <div className="flex items-start">
                <input
                  {...register('subscribeNewsletter')}
                  id="subscribe-newsletter"
                  type="checkbox"
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 dark:border-gray-600 rounded mt-0.5"
                />
                <label htmlFor="subscribe-newsletter" className="ml-2 block text-sm text-gray-900 dark:text-gray-300">
                  Send me updates about new features and tips
                </label>
              </div>
              
              {errors.agreeToTerms && (
                <p className="text-sm text-red-600 dark:text-red-400">{errors.agreeToTerms.message}</p>
              )}
            </div>

            {/* Submit Button */}
            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {isLoading ? (
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : null}
                Create account
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};