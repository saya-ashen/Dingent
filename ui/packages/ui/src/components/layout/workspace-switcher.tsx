import { ChevronsUpDown, Plus, PlusCircle } from 'lucide-react'
import { useRouter } from "next/navigation";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuTrigger,
} from '../'
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from '../'
import { useWorkspaceStore } from '@repo/store'
import { useState } from 'react'
import { CreateWorkspaceDialog } from '../common/create-workspace-dialog'


export function WorkspaceSwitcher() {
  const { workspaces, currentWorkspace: activeWorkspace } = useWorkspaceStore();
  const { isMobile } = useSidebar()
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const selectedWorkspace = activeWorkspace || workspaces[0]
  const router = useRouter();
  if (!selectedWorkspace) {
    return null
  }

  const handleSwitch = (workspaceSlug: string) => {
    router.push(`/${workspaceSlug}`);

  };
  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size='lg'
              className='data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground'
            >
              <div className='bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg'>
              </div>
              <div className='grid flex-1 text-start text-sm leading-tight'>
                <span className='truncate font-semibold'>
                  {selectedWorkspace.name}
                </span>
                <span className='truncate text-xs'>{selectedWorkspace.name}</span>
              </div>
              <ChevronsUpDown className='ms-auto' />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            className='w-(--radix-dropdown-menu-trigger-width) min-w-56 rounded-lg'
            align='start'
            side={isMobile ? 'bottom' : 'right'}
            sideOffset={4}
          >
            <DropdownMenuLabel className='text-muted-foreground text-xs'>
              Workspaces
            </DropdownMenuLabel>
            {workspaces.map((workspace, index) => (
              <DropdownMenuItem
                key={workspace.id}
                onClick={() => handleSwitch(workspace.slug)}
                className='gap-2 p-2'
              >
                <div className='flex size-6 items-center justify-center rounded-sm border'>
                </div>
                {workspace.name}
                <DropdownMenuShortcut>⌘{index + 1}</DropdownMenuShortcut>
              </DropdownMenuItem>
            ))}
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={(e) => {
              e.preventDefault(); // 防止下拉菜单关闭导致弹窗闪退
              setIsDialogOpen(true);
            }}>
              <div className="flex items-center gap-2">
                <PlusCircle className="size-4" />
                <span>Create Workspace</span>
              </div>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <CreateWorkspaceDialog
          open={isDialogOpen}
          onOpenChange={setIsDialogOpen}
        />
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
