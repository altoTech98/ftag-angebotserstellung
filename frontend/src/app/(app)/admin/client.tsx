'use client';

import { useState } from 'react';
import UserManagement from './user-management';
import AuditLog from './audit-log';
import SystemSettings from './system-settings';
import { cn } from '@/lib/utils';

type Tab = 'users' | 'audit' | 'settings';

const tabs: { id: Tab; label: string }[] = [
  { id: 'users', label: 'Benutzer' },
  { id: 'audit', label: 'Aktivitaets-Log' },
  { id: 'settings', label: 'Einstellungen' },
];

interface AdminClientProps {
  initialUsers: Array<Record<string, unknown>>;
  initialTotal: number;
  initialSettings: Record<string, unknown>;
}

export default function AdminClient({
  initialUsers,
  initialTotal,
  initialSettings,
}: AdminClientProps) {
  const [activeTab, setActiveTab] = useState<Tab>('users');

  return (
    <div>
      {/* Tab bar */}
      <div className="flex border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'px-4 py-2 text-sm font-medium transition-colors -mb-px',
              activeTab === tab.id
                ? 'border-b-2 border-primary text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="mt-6">
        {activeTab === 'users' && (
          <UserManagement
            initialUsers={initialUsers}
            initialTotal={initialTotal}
          />
        )}
        {activeTab === 'audit' && <AuditLog />}
        {activeTab === 'settings' && (
          <SystemSettings initialSettings={initialSettings} />
        )}
      </div>
    </div>
  );
}
