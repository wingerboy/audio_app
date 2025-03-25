'use client';

import { useState } from 'react';
import { Card, Switch, Select, Button } from '@/components/ui';
import { useTheme } from 'next-themes';

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [notifications, setNotifications] = useState(true);
  const [language, setLanguage] = useState('zh');

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6 text-gray-900 dark:text-white">设置</h1>
      
      <div className="space-y-6">
        {/* 主题设置 */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">显示设置</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-gray-800 dark:text-gray-200 font-medium">深色模式</label>
              <Switch
                checked={theme === 'dark'}
                onChange={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              />
            </div>
          </div>
        </Card>

        {/* 通知设置 */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">通知设置</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-gray-800 dark:text-gray-200 font-medium">启用通知</label>
              <Switch
                checked={notifications}
                onChange={setNotifications}
              />
            </div>
          </div>
        </Card>

        {/* 语言设置 */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">语言设置</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-gray-800 dark:text-gray-200 font-medium">界面语言</label>
              <Select
                value={language}
                onChange={(value) => setLanguage(value)}
                options={[
                  { value: 'zh', label: '中文' },
                  { value: 'en', label: 'English' }
                ]}
                className="w-32"
              />
            </div>
          </div>
        </Card>

        {/* 保存按钮 */}
        <div className="flex justify-end">
          <Button
            onClick={() => {
              // TODO: 保存设置
              console.log('保存设置', {
                theme,
                notifications,
                language
              });
            }}
            className="bg-blue-600 hover:bg-blue-700 text-white font-medium"
          >
            保存设置
          </Button>
        </div>
      </div>
    </div>
  );
} 