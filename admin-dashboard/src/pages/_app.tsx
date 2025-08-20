import React from 'react';
import type { AppProps } from 'next/app';
import { SWRConfig } from 'swr';
import AppLayout from '@/components/AppLayout';
import 'antd/dist/reset.css';

// SWR global configuration
const swrConfig = {
  refreshInterval: 30000, // Refresh every 30 seconds
  revalidateOnFocus: true,
  errorRetryCount: 3,
  errorRetryInterval: 5000,
  onError: (error: any) => {
    console.error('SWR Error:', error);
  },
};

export default function App({ Component, pageProps }: AppProps) {
  return (
    <SWRConfig value={swrConfig}>
      <AppLayout>
        <Component {...pageProps} />
      </AppLayout>
    </SWRConfig>
  );
}