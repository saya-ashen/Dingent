'use client';

import ChatProviders from '@/features/chat/shared/ChatProviders';

export default function Providers({ children, sidebar }: {
  children: React.ReactNode, sidebar: React.ReactNode;
}) {
  return (
    <ChatProviders sidebar={sidebar}>
      {children}
    </ChatProviders>
  );
}
