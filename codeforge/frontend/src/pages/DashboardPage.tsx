/**
 * Dashboard Page Component
 */
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  HiPlus,
  HiCode,
  HiClock,
  HiUsers,
  HiTemplate,
  HiSearch,
  HiFilter,
  HiStar,
  HiLightningBolt,
  HiCurrencyDollar
} from 'react-icons/hi';
import { formatDistanceToNow } from 'date-fns';

import { Navbar } from '../components/Layout/Navbar';
import { ProjectCard } from '../components/Projects/ProjectCard';
import { CreateProjectModal } from '../components/Projects/CreateProjectModal';
import { useAuthStore } from '../stores/authStore';
import { api } from '../services/api';

export const DashboardPage: React.FC = () => {
  const { user } = useAuthStore();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterLanguage, setFilterLanguage] = useState('all');

  // Fetch user's projects
  const { data: projects, isLoading: projectsLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.getProjects(),
  });

  // Fetch user's credits
  const { data: credits } = useQuery({
    queryKey: ['credits'],
    queryFn: () => api.getUserCredits(),
  });

  // Filter projects
  const filteredProjects = projects?.filter(project => {
    const matchesSearch = project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         project.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesLanguage = filterLanguage === 'all' || project.language === filterLanguage;
    return matchesSearch && matchesLanguage;
  });

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navbar />

      <div className="container mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Welcome back, {user?.username}!
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Build something amazing today
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <StatCard
            icon={<HiCode className="w-6 h-6" />}
            label="Projects"
            value={projects?.length || 0}
            subtext="Unlimited"
            color="blue"
          />
          <StatCard
            icon={<HiCurrencyDollar className="w-6 h-6" />}
            label="Credits"
            value={credits?.balance || 0}
            subtext={`${credits?.credits_per_hour || 0}/hr`}
            color="green"
          />
          <StatCard
            icon={<HiLightningBolt className="w-6 h-6" />}
            label="Active Containers"
            value={credits?.active_containers || 0}
            subtext="No limits"
            color="yellow"
          />
          <StatCard
            icon={<HiUsers className="w-6 h-6" />}
            label="Collaborators"
            value={projects?.reduce((acc, p) => acc + (p.collaborators?.length || 0), 0) || 0}
            subtext="Team work"
            color="purple"
          />
        </div>

        {/* Projects Section */}
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
            Your Projects
          </h2>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
          >
            <HiPlus className="w-5 h-5" />
            New Project
          </button>
        </div>

        {/* Search and Filters */}
        <div className="mb-6 flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <HiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search projects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <div className="relative">
            <HiFilter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <select
              value={filterLanguage}
              onChange={(e) => setFilterLanguage(e.target.value)}
              className="pl-10 pr-8 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent appearance-none"
            >
              <option value="all">All Languages</option>
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
              <option value="typescript">TypeScript</option>
              <option value="go">Go</option>
              <option value="rust">Rust</option>
              <option value="java">Java</option>
            </select>
          </div>
        </div>

        {/* Projects Grid */}
        {projectsLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-gray-600 dark:text-gray-400">Loading projects...</div>
          </div>
        ) : filteredProjects?.length === 0 ? (
          <div className="text-center py-20 bg-white dark:bg-gray-800 rounded-xl">
            <HiCode className="w-16 h-16 mx-auto text-gray-400 mb-4" />
            <h3 className="text-xl font-medium text-gray-900 dark:text-white mb-2">
              {searchQuery || filterLanguage !== 'all' ? 'No projects found' : 'No projects yet'}
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              {searchQuery || filterLanguage !== 'all' 
                ? 'Try adjusting your search or filters'
                : 'Create your first project to get started'
              }
            </p>
            {!searchQuery && filterLanguage === 'all' && (
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
              >
                Create Project
              </button>
            )}
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredProjects?.map(project => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        )}

        {/* Templates Section */}
        <div className="mt-12">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-6">
            Popular Templates
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
            <TemplateCard
              name="Next.js Starter"
              description="Full-stack React framework"
              language="typescript"
              stars={1234}
            />
            <TemplateCard
              name="FastAPI + React"
              description="Modern Python API"
              language="python"
              stars={892}
            />
            <TemplateCard
              name="Go Microservice"
              description="High-performance backend"
              language="go"
              stars={567}
            />
            <TemplateCard
              name="Rust WebAssembly"
              description="Browser + native speed"
              language="rust"
              stars={445}
            />
          </div>
        </div>
      </div>

      {/* Create Project Modal */}
      {showCreateModal && (
        <CreateProjectModal onClose={() => setShowCreateModal(false)} />
      )}
    </div>
  );
};

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  subtext: string;
  color: 'blue' | 'green' | 'yellow' | 'purple';
}

const StatCard: React.FC<StatCardProps> = ({ icon, label, value, subtext, color }) => {
  const colorClasses = {
    blue: 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/20',
    green: 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/20',
    yellow: 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/20',
    purple: 'text-purple-600 bg-purple-100 dark:text-purple-400 dark:bg-purple-900/20',
  };

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm">
      <div className={`inline-flex p-3 rounded-lg ${colorClasses[color]} mb-4`}>
        {icon}
      </div>
      <div className="text-2xl font-bold text-gray-900 dark:text-white">{value}</div>
      <div className="text-sm text-gray-600 dark:text-gray-400">{label}</div>
      <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">{subtext}</div>
    </div>
  );
};

interface TemplateCardProps {
  name: string;
  description: string;
  language: string;
  stars: number;
}

const TemplateCard: React.FC<TemplateCardProps> = ({ name, description, language, stars }) => {
  return (
    <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-500 dark:hover:border-primary-400 transition cursor-pointer">
      <div className="flex items-start justify-between mb-2">
        <HiTemplate className="w-8 h-8 text-gray-400" />
        <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
          <HiStar className="w-4 h-4 mr-1" />
          {stars}
        </div>
      </div>
      <h3 className="font-medium text-gray-900 dark:text-white mb-1">{name}</h3>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">{description}</p>
      <span className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded">
        {language}
      </span>
    </div>
  );
};