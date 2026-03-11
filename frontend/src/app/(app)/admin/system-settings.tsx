'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import { EyeIcon, EyeOffIcon } from 'lucide-react';
import {
  updateAnalyseSettings,
  updateSecuritySettings,
  updateApiKeySettings,
} from '@/lib/actions/admin-actions';

type SettingsSection = 'analyse' | 'security' | 'apikey';

const sections: { id: SettingsSection; label: string }[] = [
  { id: 'analyse', label: 'Analyse' },
  { id: 'security', label: 'Sicherheit' },
  { id: 'apikey', label: 'API-Schluessel' },
];

interface SystemSettingsProps {
  initialSettings: Record<string, unknown>;
}

export default function SystemSettings({ initialSettings }: SystemSettingsProps) {
  const [activeSection, setActiveSection] = useState<SettingsSection>('analyse');
  const [message, setMessage] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  // Analyse settings
  const [defaultConfidence, setDefaultConfidence] = useState(
    String(initialSettings.defaultConfidence ?? 0.7)
  );
  const [maxUploadSizeMB, setMaxUploadSizeMB] = useState(
    String(initialSettings.maxUploadSizeMB ?? 50)
  );
  const [validationPasses, setValidationPasses] = useState(
    String(initialSettings.validationPasses ?? 1)
  );

  // Security settings
  const [sessionTimeoutMin, setSessionTimeoutMin] = useState(
    String(initialSettings.sessionTimeoutMin ?? 480)
  );

  // API key settings
  const [claudeApiKey, setClaudeApiKey] = useState(
    (initialSettings.claudeApiKey as string) ?? ''
  );
  const [showApiKey, setShowApiKey] = useState(false);

  async function handleSaveAnalyse() {
    try {
      const formData = new FormData();
      formData.set('defaultConfidence', defaultConfidence);
      formData.set('maxUploadSizeMB', maxUploadSizeMB);
      formData.set('validationPasses', validationPasses);
      await updateAnalyseSettings(formData);
      setMessage({ type: 'success', text: 'Analyse-Einstellungen gespeichert' });
    } catch (err) {
      setMessage({ type: 'error', text: (err as Error).message });
    }
  }

  async function handleSaveSecurity() {
    try {
      const formData = new FormData();
      formData.set('sessionTimeoutMin', sessionTimeoutMin);
      await updateSecuritySettings(formData);
      setMessage({
        type: 'success',
        text: 'Sicherheits-Einstellungen gespeichert',
      });
    } catch (err) {
      setMessage({ type: 'error', text: (err as Error).message });
    }
  }

  async function handleSaveApiKey() {
    try {
      const formData = new FormData();
      formData.set('claudeApiKey', claudeApiKey);
      await updateApiKeySettings(formData);
      setMessage({ type: 'success', text: 'API-Schluessel gespeichert' });
    } catch (err) {
      setMessage({ type: 'error', text: (err as Error).message });
    }
  }

  return (
    <div className="space-y-4">
      {/* Section tabs */}
      <div className="flex gap-2">
        {sections.map((section) => (
          <Button
            key={section.id}
            variant={activeSection === section.id ? 'default' : 'outline'}
            size="sm"
            onClick={() => setActiveSection(section.id)}
          >
            {section.label}
          </Button>
        ))}
      </div>

      {/* Status message */}
      {message && (
        <div
          className={cn(
            'rounded-lg border px-4 py-2 text-sm',
            message.type === 'success'
              ? 'border-green-200 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200'
              : 'border-red-200 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200'
          )}
        >
          {message.text}
          <button
            onClick={() => setMessage(null)}
            className="ml-2 font-medium underline"
          >
            Schliessen
          </button>
        </div>
      )}

      {/* Analyse section */}
      {activeSection === 'analyse' && (
        <div className="rounded-lg border border-border bg-card p-6 space-y-4">
          <h3 className="text-lg font-medium">Analyse-Einstellungen</h3>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="defaultConfidence">
                Standard-Konfidenz (0–1)
              </Label>
              <Input
                id="defaultConfidence"
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={defaultConfidence}
                onChange={(e) => setDefaultConfidence(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="maxUploadSizeMB">
                Max. Upload-Groesse (MB)
              </Label>
              <Input
                id="maxUploadSizeMB"
                type="number"
                min="1"
                value={maxUploadSizeMB}
                onChange={(e) => setMaxUploadSizeMB(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="validationPasses">
                Validierungsdurchlaeufe (1–5)
              </Label>
              <Input
                id="validationPasses"
                type="number"
                min="1"
                max="5"
                value={validationPasses}
                onChange={(e) => setValidationPasses(e.target.value)}
              />
            </div>
          </div>

          <div className="pt-2">
            <Button onClick={handleSaveAnalyse}>Speichern</Button>
          </div>
        </div>
      )}

      {/* Sicherheit section */}
      {activeSection === 'security' && (
        <div className="rounded-lg border border-border bg-card p-6 space-y-4">
          <h3 className="text-lg font-medium">Sicherheits-Einstellungen</h3>

          <div className="max-w-xs space-y-2">
            <Label htmlFor="sessionTimeoutMin">
              Session-Timeout (Minuten, 15–1440)
            </Label>
            <Input
              id="sessionTimeoutMin"
              type="number"
              min="15"
              max="1440"
              value={sessionTimeoutMin}
              onChange={(e) => setSessionTimeoutMin(e.target.value)}
            />
          </div>

          <div className="pt-2">
            <Button onClick={handleSaveSecurity}>Speichern</Button>
          </div>
        </div>
      )}

      {/* API-Schluessel section */}
      {activeSection === 'apikey' && (
        <div className="rounded-lg border border-border bg-card p-6 space-y-4">
          <h3 className="text-lg font-medium">API-Schluessel</h3>

          <div className="max-w-md space-y-2">
            <Label htmlFor="claudeApiKey">Claude API-Schluessel</Label>
            <div className="relative">
              <Input
                id="claudeApiKey"
                type={showApiKey ? 'text' : 'password'}
                value={claudeApiKey}
                onChange={(e) => setClaudeApiKey(e.target.value)}
                placeholder="sk-ant-..."
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showApiKey ? (
                  <EyeOffIcon className="size-4" />
                ) : (
                  <EyeIcon className="size-4" />
                )}
              </button>
            </div>
            <p className="text-xs text-muted-foreground">
              Wird serverseitig gespeichert und verschluesselt uebertragen
            </p>
          </div>

          <div className="pt-2">
            <Button onClick={handleSaveApiKey}>Speichern</Button>
          </div>
        </div>
      )}
    </div>
  );
}
