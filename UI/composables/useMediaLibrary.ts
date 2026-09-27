import { mediaLibraryStore, importFiles, importUrl, importBlob } from "@elah/core"
import type { MediaAsset } from "@elah/core"

/**
 * useMediaLibrary — reactive Vue bridge over @elah/core's vanilla zustand
 * mediaLibraryStore. Exposes the asset list (insertion order) plus the SDK
 * import helpers; mutations go straight to the store.
 */
export function useMediaLibrary() {
  const tick = shallowRef(0)
  const unsub = mediaLibraryStore.subscribe(() => {
    tick.value++
  })
  onScopeDispose(unsub)

  const assets = computed<MediaAsset[]>(() => {
    tick.value // track store versions
    const s = mediaLibraryStore.getState()
    return s.order.map((id) => s.assets[id]).filter((a): a is MediaAsset => Boolean(a))
  })

  const removeAsset = (id: string) => mediaLibraryStore.getState().removeAsset(id)
  const getAsset = (id: string) => mediaLibraryStore.getState().getAsset(id)

  return { assets, removeAsset, getAsset, importFiles, importUrl, importBlob }
}
