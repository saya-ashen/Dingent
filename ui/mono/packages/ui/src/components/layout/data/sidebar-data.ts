import {
  LayoutDashboard,
  Monitor,
  HelpCircle,
  Bell,
  Palette,
  Settings,
  Wrench,
  UserCog,
  FileText,
  Bot,
  Workflow,
  Store,
} from 'lucide-react'
import { type SidebarData } from '../types'

export const sidebarData: SidebarData = {
  user: {
    name: 'admin',
    email: 'admin@admin.com',
    avatar: '/avatars/shadcn.jpg',
  },
  teams: [],
  navGroups: [
    {
      title: 'General',
      items: [
        {
          title: 'Dashboard',
          url: '/',
          icon: LayoutDashboard,
        },
        {
          title: 'Assistants',
          url: '/assistants',
          icon: Bot,
        },
        {
          title: 'Workflows',
          url: '/workflows',
          icon: Workflow,
        },
        {
          title: 'Plugins',
          url: '/plugins',
          icon: Store,
        },
        {
          title: 'Market',
          url: '/market',
          icon: Store,
        },
        {
          title: 'Agent Settings',
          url: '/agent-settings',
          icon: Settings,
        },
        {
          title: 'Logs',
          url: '/system-logs',
          icon: FileText,
        },
      ],
    },
    {
      title: 'Under Construction Pages',
      items: [
        {
          title: 'Settings',
          icon: Settings,
          items: [
            {
              title: 'Profile',
              url: '/settings',
              icon: UserCog,
            },
            {
              title: 'Account',
              url: '/settings/account',
              icon: Wrench,
            },
            {
              title: 'Appearance',
              url: '/settings/appearance',
              icon: Palette,
            },
            {
              title: 'Notifications',
              url: '/settings/notifications',
              icon: Bell,
            },
            {
              title: 'Display',
              url: '/settings/display',
              icon: Monitor,
            },
          ],
        },
        {
          title: 'Help Center',
          url: '/help-center',
          icon: HelpCircle,
        },
      ],
    },
  ],
}
