import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { Moon, Sun, Check } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Settings() {
  const { user } = useAuth()
  const { theme, toggleTheme } = useTheme()
  
  const [preferences, setPreferences] = useState({
    notifications: {
      email: true,
      slack: false,
      inApp: true,
    },
    voting: {
      autoApproveBelow: 50,
      requireApprovalAbove: 500,
      defaultDelegate: '',
    },
    general: {
      language: 'en',
      timezone: 'UTC',
    },
  })

  const handleSavePreferences = () => {
    // Save preferences logic
    console.log('Saving preferences:', preferences)
    toast.success('Settings saved successfully')
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Manage your account preferences and notifications
        </p>
      </div>

      {/* Account Section */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">Account</h2>
        </div>
        <div className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Email Address
            </label>
            <p className="mt-1 text-sm text-gray-900 dark:text-white">{user?.email}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Account ID
            </label>
            <p className="mt-1 text-sm text-gray-900 dark:text-white font-mono">{user?.id}</p>
          </div>
        </div>
      </div>

      {/* Appearance Section */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">Appearance</h2>
        </div>
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-gray-900 dark:text-white">Dark Mode</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Use dark theme for better visibility in low light
              </p>
            </div>
            <button
              onClick={toggleTheme}
              className="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 bg-gray-200 dark:bg-gray-700"
            >
              <span
                className={`${
                  theme === 'dark' ? 'translate-x-5' : 'translate-x-0'
                } pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out`}
              />
              <span className="sr-only">Toggle dark mode</span>
              <span className="absolute inset-0 flex items-center justify-between px-1">
                <Sun className="h-3 w-3 text-gray-400" />
                <Moon className="h-3 w-3 text-gray-600" />
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* Notifications Section */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">Notifications</h2>
        </div>
        <div className="px-6 py-4 space-y-4">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={preferences.notifications.email}
              onChange={(e) => setPreferences({
                ...preferences,
                notifications: { ...preferences.notifications, email: e.target.checked }
              })}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <span className="ml-3">
              <span className="text-sm font-medium text-gray-900 dark:text-white">Email notifications</span>
              <span className="text-sm text-gray-500 dark:text-gray-400 block">
                Receive updates about tasks and votes via email
              </span>
            </span>
          </label>

          <label className="flex items-center">
            <input
              type="checkbox"
              checked={preferences.notifications.slack}
              onChange={(e) => setPreferences({
                ...preferences,
                notifications: { ...preferences.notifications, slack: e.target.checked }
              })}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <span className="ml-3">
              <span className="text-sm font-medium text-gray-900 dark:text-white">Slack notifications</span>
              <span className="text-sm text-gray-500 dark:text-gray-400 block">
                Get notified in your Slack workspace
              </span>
            </span>
          </label>

          <label className="flex items-center">
            <input
              type="checkbox"
              checked={preferences.notifications.inApp}
              onChange={(e) => setPreferences({
                ...preferences,
                notifications: { ...preferences.notifications, inApp: e.target.checked }
              })}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <span className="ml-3">
              <span className="text-sm font-medium text-gray-900 dark:text-white">In-app notifications</span>
              <span className="text-sm text-gray-500 dark:text-gray-400 block">
                Show notifications within the application
              </span>
            </span>
          </label>
        </div>
      </div>

      {/* Voting Preferences Section */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">Voting Preferences</h2>
        </div>
        <div className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Auto-approve tasks below ($)
            </label>
            <input
              type="number"
              value={preferences.voting.autoApproveBelow}
              onChange={(e) => setPreferences({
                ...preferences,
                voting: { ...preferences.voting, autoApproveBelow: parseInt(e.target.value) || 0 }
              })}
              className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:bg-gray-700 dark:text-white"
            />
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Tasks with cost below this amount will be auto-approved
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Require approval above ($)
            </label>
            <input
              type="number"
              value={preferences.voting.requireApprovalAbove}
              onChange={(e) => setPreferences({
                ...preferences,
                voting: { ...preferences.voting, requireApprovalAbove: parseInt(e.target.value) || 0 }
              })}
              className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:bg-gray-700 dark:text-white"
            />
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Tasks above this amount will always require manual approval
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Default delegate
            </label>
            <input
              type="text"
              value={preferences.voting.defaultDelegate}
              onChange={(e) => setPreferences({
                ...preferences,
                voting: { ...preferences.voting, defaultDelegate: e.target.value }
              })}
              placeholder="user@example.com"
              className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:bg-gray-700 dark:text-white"
            />
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Delegate voting rights to another team member when you're away
            </p>
          </div>
        </div>
      </div>

      {/* General Section */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">General</h2>
        </div>
        <div className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Language
            </label>
            <select
              value={preferences.general.language}
              onChange={(e) => setPreferences({
                ...preferences,
                general: { ...preferences.general, language: e.target.value }
              })}
              className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:bg-gray-700 dark:text-white"
            >
              <option value="en">English</option>
              <option value="es">Español</option>
              <option value="fr">Français</option>
              <option value="de">Deutsch</option>
              <option value="ja">日本語</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Timezone
            </label>
            <select
              value={preferences.general.timezone}
              onChange={(e) => setPreferences({
                ...preferences,
                general: { ...preferences.general, timezone: e.target.value }
              })}
              className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:bg-gray-700 dark:text-white"
            >
              <option value="UTC">UTC</option>
              <option value="America/New_York">Eastern Time</option>
              <option value="America/Chicago">Central Time</option>
              <option value="America/Denver">Mountain Time</option>
              <option value="America/Los_Angeles">Pacific Time</option>
              <option value="Europe/London">London</option>
              <option value="Europe/Paris">Paris</option>
              <option value="Asia/Tokyo">Tokyo</option>
            </select>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSavePreferences}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
        >
          <Check className="h-4 w-4 mr-2" />
          Save Settings
        </button>
      </div>
    </div>
  )
}