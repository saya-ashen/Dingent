import {
  LayoutDashboard,
  FileText,
  Bot,
  Workflow,
  Store,
  Construction
} from "lucide-react";
import { type SidebarData } from "@repo/ui/components";

export const sidebarData: SidebarData = {
  user: {
    name: "admin",
    email: "admin@admin.com",
    avatar: "/avatars/shadcn.jpg",
  },
  teams: [],
  navGroups: [
    {
      title: "General",
      items: [
        {
          title: "Overview",
          url: "/overview",
          icon: LayoutDashboard,
        },
        {
          title: "Assistants",
          url: "/assistants",
          icon: Bot,
        },
        {
          title: "Workflows",
          url: "/workflows",
          icon: Workflow,
        },
        {
          title: "Plugins",
          url: "/plugins",
          icon: Store,
        },
        {
          title: "Market",
          url: "/market",
          icon: Store,
        },
        {
          title: "Logs",
          url: "/system-logs",
          icon: FileText,
        },
        {
          title: "Chat Interface",
          url: "/system-logs",
          icon: Construction,
        },
      ],
    },
    // {
    //   title: "Under Construction Pages",
    //   items: [
    //     {
    //       title: "Settings",
    //       icon: Settings,
    //       items: [
    //         {
    //           title: "Profile",
    //           url: "/settings",
    //           icon: UserCog,
    //         },
    //         {
    //           title: "Account",
    //           url: "/settings/account",
    //           icon: Wrench,
    //         },
    //         {
    //           title: "Appearance",
    //           url: "/settings/appearance",
    //           icon: Palette,
    //         },
    //         {
    //           title: "Notifications",
    //           url: "/settings/notifications",
    //           icon: Bell,
    //         },
    //         {
    //           title: "Display",
    //           url: "/settings/display",
    //           icon: Monitor,
    //         },
    //       ],
    //     },
    //     {
    //       title: "Help Center",
    //       url: "/help-center",
    //       icon: HelpCircle,
    //     },
    //   ],
    // },
  ],
};
