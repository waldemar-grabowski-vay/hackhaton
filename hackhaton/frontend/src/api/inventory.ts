/**
 * Inventory API hook.
 *
 * 002 / FR-013a — `useRefreshInventory` from 001 is retired along
 * with the cache + sync layer. The inventory is re-read from the
 * operator's local `ree-vehicle-configs` clone on every
 * `GET /api/inventory` request; the operator's `git pull` + browser
 * tab refresh is the v1 update flow.
 */
import { useQuery } from "@tanstack/react-query";

import { ApiError, apiRequest } from "@/api/client";
import { Inventory, inventorySchema } from "@/api/schemas";

const INVENTORY_QUERY_KEY = ["inventory"] as const;

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
