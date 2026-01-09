"use client";

import { useState } from "react";
import { Edit2, Trash2, CheckCircle, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import type { LLMModelConfig, LLMModelConfigUpdate, TestConnectionRequest, TestConnectionResponse } from "@/types/entity";
import { ModelConfigDialog } from "./model-config-dialog";

interface ModelsTableProps {
  models: LLMModelConfig[];
  onEdit: (id: string, data: LLMModelConfigUpdate) => void;
  onDelete: (id: string) => void;
  onTestConnection?: (data: TestConnectionRequest) => Promise<TestConnectionResponse>;
  isUpdating: boolean;
  isDeleting: boolean;
  deletingId?: string;
}

export function ModelsTable({
  models,
  onEdit,
  onDelete,
  onTestConnection,
  isUpdating,
  isDeleting,
  deletingId,
}: ModelsTableProps) {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [modelToDelete, setModelToDelete] = useState<string | null>(null);

  const handleDeleteClick = (id: string) => {
    setModelToDelete(id);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = () => {
    if (modelToDelete) {
      onDelete(modelToDelete);
    }
    setDeleteDialogOpen(false);
    setModelToDelete(null);
  };

  if (models.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-muted-foreground">No model configurations yet.</p>
        <p className="text-sm text-muted-foreground">
          Add a model configuration to get started.
        </p>
      </div>
    );
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Provider</TableHead>
            <TableHead>Model</TableHead>
            <TableHead>API Base</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>API Key</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {models.map((model) => (
            <TableRow key={model.id}>
              <TableCell className="font-medium">{model.name}</TableCell>
              <TableCell>
                <Badge variant="outline">{model.provider}</Badge>
              </TableCell>
              <TableCell>{model.model}</TableCell>
              <TableCell className="max-w-[200px] truncate">
                {model.api_base || "-"}
              </TableCell>
              <TableCell>
                {model.is_active ? (
                  <Badge variant="default" className="gap-1">
                    <CheckCircle className="h-3 w-3" />
                    Active
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="gap-1">
                    <XCircle className="h-3 w-3" />
                    Inactive
                  </Badge>
                )}
              </TableCell>
              <TableCell>
                {model.has_api_key ? (
                  <Badge variant="outline">Configured</Badge>
                ) : (
                  <Badge variant="secondary">Not Set</Badge>
                )}
              </TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-2">
                  <ModelConfigDialog
                    model={model}
                    isPending={isUpdating}
                    onSave={(data) => onEdit(model.id, data)}
                    onTestConnection={onTestConnection}
                    trigger={
                      <Button variant="ghost" size="sm">
                        <Edit2 className="h-4 w-4" />
                      </Button>
                    }
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteClick(model.id)}
                    disabled={isDeleting && deletingId === model.id}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Model Configuration</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this model configuration? This
              action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmDelete}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
