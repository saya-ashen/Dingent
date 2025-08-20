import { StatusLevel } from '@/types';

// Status level mapping based on the Python implementation
export const getStatusLevel = (text: string): StatusLevel => {
  const lowerText = text.toLowerCase();
  
  if (lowerText.includes('error') || lowerText.includes('fail') || lowerText.includes('exception')) {
    return 'error';
  }
  if (lowerText.includes('warn') || lowerText.includes('warning')) {
    return 'warn';
  }
  if (lowerText.includes('ok') || lowerText.includes('success') || lowerText.includes('running')) {
    return 'ok';
  }
  return 'unknown';
};

// Get effective status for assistant (disabled takes precedence)
export const getEffectiveAssistantStatus = (rawStatus: any, enabled: boolean): [StatusLevel, string] => {
  if (!enabled) {
    return ['disabled', 'Disabled'];
  }
  
  const text = rawStatus?.toString() || 'Unknown';
  const level = getStatusLevel(text);
  
  const labelMap = {
    ok: 'OK',
    warn: 'Warning', 
    error: 'Error',
    unknown: 'Unknown'
  };
  
  const friendly = `${labelMap[level as keyof typeof labelMap] || 'Unknown'} (${text})`;
  return [level, friendly];
};

// Get effective status for plugin (same logic as assistant)
export const getEffectivePluginStatus = (rawStatus: any, enabled: boolean): [StatusLevel, string] => {
  return getEffectiveAssistantStatus(rawStatus, enabled);
};

// Format timestamp for display
export const formatTimestamp = (timestamp: string): string => {
  return new Date(timestamp).toLocaleString();
};

// Safe boolean conversion
export const safeBool = (value: any, defaultValue = false): boolean => {
  if (typeof value === 'boolean') return value;
  if (value === null || value === undefined || value === '' || value === 'None') return defaultValue;
  if (typeof value === 'number') return Boolean(value);
  if (typeof value === 'string') {
    return ['1', 'true', 't', 'yes', 'y', 'on'].includes(value.trim().toLowerCase());
  }
  return defaultValue;
};

// Safe string conversion  
export const safeString = (value: any): string => {
  return value === null || value === undefined ? '' : String(value);
};

// Status colors for Ant Design
export const getStatusColor = (level: StatusLevel): string => {
  switch (level) {
    case 'ok': return 'success';
    case 'warn': return 'warning';
    case 'error': return 'error';
    case 'disabled': return 'default';
    default: return 'default';
  }
};

// Status text colors
export const getStatusTextColor = (level: string): string => {
  switch (level.toLowerCase()) {
    case 'error': return '#ff4d4f';
    case 'warning': case 'warn': return '#faad14';
    case 'info': return '#1890ff';
    case 'debug': return '#52c41a';
    default: return '#000000d9';
  }
};