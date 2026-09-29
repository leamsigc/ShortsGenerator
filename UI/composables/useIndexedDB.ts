const DB_NAME = 'SocialLeadGenDB'
const DB_VERSION = 3

let dbInstance: IDBDatabase | null = null

function openDB(): Promise<IDBDatabase> {
  if (dbInstance) return Promise.resolve(dbInstance)
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = (e) => {
      const db = (e.target as IDBOpenDBRequest).result
      if (!db.objectStoreNames.contains('profiles')) {
        db.createObjectStore('profiles', { keyPath: 'id' })
      }
      if (!db.objectStoreNames.contains('audits')) {
        db.createObjectStore('audits', { keyPath: 'username' })
      }
      if (!db.objectStoreNames.contains('posts')) {
        const ps = db.createObjectStore('posts', { keyPath: 'id', autoIncrement: true })
        ps.createIndex('campaignId', 'campaignId', { unique: false })
      }
      if (!db.objectStoreNames.contains('campaigns')) {
        db.createObjectStore('campaigns', { keyPath: 'id' })
      }
      if (!db.objectStoreNames.contains('engagement_suggestions')) {
        const es = db.createObjectStore('engagement_suggestions', { keyPath: 'id', autoIncrement: true })
        es.createIndex('postId', 'postId', { unique: false })
        es.createIndex('campaignId', 'campaignId', { unique: false })
      }
      if (!db.objectStoreNames.contains('scraped_sites')) {
        db.createObjectStore('scraped_sites', { keyPath: 'url' })
      }
      if (!db.objectStoreNames.contains('custom_voices')) {
        db.createObjectStore('custom_voices', { keyPath: 'name' })
      }
    }
    req.onsuccess = (e) => {
      dbInstance = (e.target as IDBOpenDBRequest).result
      resolve(dbInstance!)
    }
    req.onerror = () => reject(req.error)
  })
}

function getStore(name: string, mode: IDBTransactionMode = 'readonly') {
  return openDB().then(db => db.transaction(name, mode).objectStore(name))
}

export const useIndexedDB = () => {

  const saveProfile = async (profile: any) => {
    const store = await getStore('profiles', 'readwrite')
    store.put(profile)
  }

  const getProfile = async (id: string): Promise<any | null> => {
    const store = await getStore('profiles')
    return new Promise((resolve, reject) => {
      const req = store.get(id)
      req.onsuccess = () => resolve(req.result || null)
      req.onerror = () => reject(req.error)
    })
  }

  const saveAudit = async (username: string, data: any) => {
    const store = await getStore('audits', 'readwrite')
    store.put({ username, ...data })
  }

  const getAudit = async (username: string): Promise<any | null> => {
    const store = await getStore('audits')
    return new Promise((resolve, reject) => {
      const req = store.get(username)
      req.onsuccess = () => resolve(req.result || null)
      req.onerror = () => reject(req.error)
    })
  }

  const savePosts = async (posts: any[], campaignId: string) => {
    const store = await getStore('posts', 'readwrite')
    for (const p of posts) {
      store.put({ ...p, campaignId, savedAt: Date.now() })
    }
  }

  const getPostsByCampaign = async (campaignId: string): Promise<any[]> => {
    const store = await getStore('posts')
    const index = store.index('campaignId')
    return new Promise((resolve, reject) => {
      const req = index.getAll(campaignId)
      req.onsuccess = () => resolve(req.result || [])
      req.onerror = () => reject(req.error)
    })
  }

  const saveEngagementSuggestions = async (suggestions: any[], campaignId: string) => {
    const store = await getStore('engagement_suggestions', 'readwrite')
    for (const s of suggestions) {
      store.put({ ...s, campaignId, savedAt: Date.now() })
    }
  }

  const getEngagementByCampaign = async (campaignId: string): Promise<any[]> => {
    const store = await getStore('engagement_suggestions')
    const index = store.index('campaignId')
    return new Promise((resolve, reject) => {
      const req = index.getAll(campaignId)
      req.onsuccess = () => resolve(req.result || [])
      req.onerror = () => reject(req.error)
    })
  }

  const saveCampaign = async (campaign: any) => {
    const store = await getStore('campaigns', 'readwrite')
    store.put({ ...campaign, savedAt: Date.now() })
  }

  const getCampaign = async (id: string): Promise<any | null> => {
    const store = await getStore('campaigns')
    return new Promise((resolve, reject) => {
      const req = store.get(id)
      req.onsuccess = () => resolve(req.result || null)
      req.onerror = () => reject(req.error)
    })
  }

  const saveScrapedSite = async (data: any) => {
    const store = await getStore('scraped_sites', 'readwrite')
    store.put({ ...data, savedAt: Date.now() })
  }

  const getScrapedSite = async (url: string): Promise<any | null> => {
    const store = await getStore('scraped_sites')
    return new Promise((resolve, reject) => {
      const req = store.get(url)
      req.onsuccess = () => resolve(req.result || null)
      req.onerror = () => reject(req.error)
    })
  }

  const getAllCampaigns = async (): Promise<any[]> => {
    const store = await getStore('campaigns')
    return new Promise((resolve, reject) => {
      const req = store.getAll()
      req.onsuccess = () => resolve(req.result || [])
      req.onerror = () => reject(req.error)
    })
  }

  const saveCustomVoice = async (voice: any) => {
    const store = await getStore('custom_voices', 'readwrite')
    return new Promise<void>((resolve, reject) => {
      const req = store.put({ ...voice, updatedAt: Date.now() })
      req.onsuccess = () => resolve()
      req.onerror = () => reject(req.error)
    })
  }

  const getCustomVoice = async (name: string): Promise<any | null> => {
    const store = await getStore('custom_voices')
    return new Promise((resolve, reject) => {
      const req = store.get(name)
      req.onsuccess = () => resolve(req.result || null)
      req.onerror = () => reject(req.error)
    })
  }

  const getAllCustomVoices = async (): Promise<any[]> => {
    const store = await getStore('custom_voices')
    return new Promise((resolve, reject) => {
      const req = store.getAll()
      req.onsuccess = () => resolve(req.result || [])
      req.onerror = () => reject(req.error)
    })
  }

  const deleteCustomVoice = async (name: string) => {
    const store = await getStore('custom_voices', 'readwrite')
    return new Promise<void>((resolve, reject) => {
      const req = store.delete(name)
      req.onsuccess = () => resolve()
      req.onerror = () => reject(req.error)
    })
  }

  return {
    saveProfile,
    getProfile,
    saveAudit,
    getAudit,
    savePosts,
    getPostsByCampaign,
    saveEngagementSuggestions,
    getEngagementByCampaign,
    saveCampaign,
    getCampaign,
    getAllCampaigns,
    saveScrapedSite,
    getScrapedSite,
    saveCustomVoice,
    getCustomVoice,
    getAllCustomVoices,
    deleteCustomVoice,
  }
}
