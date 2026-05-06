/**
 * Inventory API hooks (T039).
 *
 * `useInventory` exposes the cached host list to the wizard.
 * `useRefreshInventory` wraps `POST /api/inventory/refresh` and surfaces a toast
 * on failure (R2 — refresh failures keep the previous list intact).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiRequest } from "@/api/client";
import { Inventory, inventoryMetaSchema, inventorySchema } from "@/api/schemas";
import { useToast } from "@/lib/hooks/use-toast";
import { strings } from "@/strings";
import { z } from "zod";

const INVENTORY_QUERY_KEY = ["inventory"] as const;

const refreshResponseSchema = z.object({ meta: inventoryMetaSchema });

export function useInventory() {
  return useQuery<Inventory, ApiError>({
    queryKey: INVENTORY_QUERY_KEY,
    queryFn: () =>
      apiRequest({
        method: "GET",
        path: "/api/inventory",
        responseSchema: inventorySchema,
      }),
    retry: false,
  });
}

export function useRefreshInventory() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: () =>
      apiRequest({
        method: "POST",
        path: "/api/inventory/refresh",
        responseSchema: refreshResponseSchema,
      }),
    onSuccess: () => {
      // Refresh succeeded; re-fetch the inventory itself for fresh hosts.
      void queryClient.invalidateQueries({ queryKey: INVENTORY_QUERY_KEY });
    },
    onError: (err) => {
      // Refresh failed; previous inventory remains intact (R2). Surface a toast.
      const isUnavailable = err instanceof ApiError && err.code === "inventory_refresh_failed";
      toast({
        variant: "destructive",
        title: strings.inventory.refreshFailedToast.title,
        description: isUnavailable
          ? strings.inventory.refreshFailedToast.body
          : strings.errors.generic,
      });
    },
  });
}
