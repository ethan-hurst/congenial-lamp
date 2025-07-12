/**
 * Landing Page Component
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { HiCode, HiLightningBolt, HiCurrencyDollar, HiGlobe } from 'react-icons/hi';

export const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 dark:from-gray-900 dark:to-gray-800">
      {/* Navigation */}
      <nav className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <HiCode className="w-8 h-8 text-primary-600 dark:text-primary-400" />
            <span className="text-2xl font-bold text-gray-900 dark:text-white">CodeForge</span>
          </div>
          <div className="flex items-center space-x-6">
            <Link to="/login" className="text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400">
              Login
            </Link>
            <Link
              to="/signup"
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
            >
              Get Started Free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="container mx-auto px-6 py-20">
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 dark:text-white mb-6">
            Cloud Development Without Limits
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-400 mb-8">
            10x better than Replit. Unlimited projects, transparent pricing, any IDE, instant cloning.
            Build anything, anywhere, with anyone.
          </p>
          <div className="flex justify-center space-x-4">
            <Link
              to="/signup"
              className="px-8 py-3 bg-primary-600 text-white text-lg font-medium rounded-lg hover:bg-primary-700 transition"
            >
              Start Coding Now
            </Link>
            <a
              href="#features"
              className="px-8 py-3 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-lg font-medium rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition"
            >
              Learn More
            </a>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="container mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold text-center text-gray-900 dark:text-white mb-12">
          Why CodeForge is Different
        </h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          <FeatureCard
            icon={<HiLightningBolt className="w-8 h-8" />}
            title="Instant Everything"
            description="Zero cold starts, instant cloning, pre-warmed containers. Start coding in milliseconds, not minutes."
          />
          <FeatureCard
            icon={<HiCurrencyDollar className="w-8 h-8" />}
            title="Pay for Compute Only"
            description="$10/month = 1000 credits. Free development tier. Unused credits roll over. Earn by contributing."
          />
          <FeatureCard
            icon={<HiCode className="w-8 h-8" />}
            title="Any IDE, Anywhere"
            description="Use VS Code, JetBrains, Vim, or our web editor. Full cloud backend for any development tool."
          />
          <FeatureCard
            icon={<HiGlobe className="w-8 h-8" />}
            title="No Limits"
            description="Unlimited projects, 64+ cores, 256GB+ RAM, GPU support. Scale infinitely with no restrictions."
          />
        </div>
      </section>

      {/* Comparison Table */}
      <section className="container mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold text-center text-gray-900 dark:text-white mb-12">
          CodeForge vs Replit
        </h2>
        <div className="max-w-4xl mx-auto bg-white dark:bg-gray-800 rounded-xl shadow-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-4 text-left text-gray-700 dark:text-gray-300">Feature</th>
                <th className="px-6 py-4 text-center text-primary-600 dark:text-primary-400 font-bold">CodeForge</th>
                <th className="px-6 py-4 text-center text-gray-700 dark:text-gray-300">Replit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              <ComparisonRow feature="Free Projects" codeforge="Unlimited" replit="3" />
              <ComparisonRow feature="CPU Cores" codeforge="64+" replit="0.5-4" />
              <ComparisonRow feature="RAM" codeforge="256GB+" replit="0.5-8GB" />
              <ComparisonRow feature="Cold Starts" codeforge="Never" replit="30-60s" />
              <ComparisonRow feature="IDE Support" codeforge="Any IDE" replit="Web only" />
              <ComparisonRow feature="Pricing" codeforge="$0.01/credit" replit="$20+/month" />
              <ComparisonRow feature="GPU Access" codeforge="✓" replit="Limited" />
              <ComparisonRow feature="Time-Travel Debug" codeforge="✓" replit="✗" />
            </tbody>
          </table>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-6 py-20">
        <div className="bg-primary-600 dark:bg-primary-700 rounded-2xl p-12 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to Build Without Limits?
          </h2>
          <p className="text-xl text-primary-100 mb-8">
            Join thousands of developers who switched from Replit
          </p>
          <Link
            to="/signup"
            className="inline-block px-8 py-3 bg-white text-primary-600 text-lg font-medium rounded-lg hover:bg-gray-100 transition"
          >
            Start Free with 100 Credits
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="container mx-auto px-6 py-8 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <p className="text-gray-600 dark:text-gray-400">
            © 2024 CodeForge. All rights reserved.
          </p>
          <div className="flex space-x-6">
            <a href="#" className="text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400">
              Documentation
            </a>
            <a href="#" className="text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400">
              GitHub
            </a>
            <a href="#" className="text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400">
              Discord
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
};

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

const FeatureCard: React.FC<FeatureCardProps> = ({ icon, title, description }) => {
  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg">
      <div className="text-primary-600 dark:text-primary-400 mb-4">{icon}</div>
      <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">{title}</h3>
      <p className="text-gray-600 dark:text-gray-400">{description}</p>
    </div>
  );
};

interface ComparisonRowProps {
  feature: string;
  codeforge: string;
  replit: string;
}

const ComparisonRow: React.FC<ComparisonRowProps> = ({ feature, codeforge, replit }) => {
  return (
    <tr>
      <td className="px-6 py-4 text-gray-700 dark:text-gray-300">{feature}</td>
      <td className="px-6 py-4 text-center font-medium text-primary-600 dark:text-primary-400">{codeforge}</td>
      <td className="px-6 py-4 text-center text-gray-600 dark:text-gray-400">{replit}</td>
    </tr>
  );
};