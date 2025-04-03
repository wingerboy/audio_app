'use client';

import { UserProfile } from '@/components/UserProfile';
import { ProtectedRoute } from '@/components/ProtectedRoute';

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">个人中心</h1>
        <UserProfile />
      </div>
    </ProtectedRoute>
  );
} 