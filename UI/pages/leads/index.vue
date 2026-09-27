<script lang="ts" setup>
interface LeadResult {
  id: string
  platform: string
  username: string
  display_name: string | null
  profile_url: string
  avatar_url: string | null
  post_url: string | null
  post_text: string | null
  follower_count: number | null
  following_count: number | null
  bio: string | null
  is_verified: boolean
  source: string
  intent_score: number
  status: string
}

interface CampaignEnrichment {
  refined_name: string
  keywords: string[]
  competitor_keywords: string[]
  target_audience: string
  intent_queries: string[]
  pain_points: string[]
  steal_audience_angle: string
  competitor_tracking?: string[]
  viral_content_angles?: string[]
  value_proposition?: string
  website_url?: string
}

interface Campaign {
  id: string
  name: string
  description: string
  keywords: string[]
  competitor_keywords: string[]
  platform: string
  platforms: string[]
  target_audience: string
  intent_queries: string[]
  pain_points: string[]
  steal_audience_angle: string
  enriched: CampaignEnrichment
  website_url: string
  competitor_tracking: string[]
  viral_content_angles: string[]
  value_proposition: string
  competitors: any[]
  viral_posts: any[]
  alert_settings: { email: string; slack: string; enabled: boolean }
  status: string
  created_at: string
  lead_count: number
  leads?: LeadResult[]
}

interface ProfileAnalysis {
  audience_demographics: string
  content_themes: string[]
  engagement_hooks: string[]
  steal_audience_strategy: string
  competitor_overlap: string[]
  recommended_outreach: string
  intent_signals: string[]
}

const { saveProfile, getProfile, saveAudit, getAudit, savePosts, getPostsByCampaign, saveEngagementSuggestions, getEngagementByCampaign, saveCampaign, getCampaign, getAllCampaigns, saveScrapedSite, getScrapedSite } = useIndexedDB()

const API_URL = "http://localhost:8080"
const activeTab = ref<'search' | 'campaigns'>('search')
const selectedCampaignId = ref<string | null>(null)

// Chrome connection
const chromePort = ref(9222)
const chromeStatus = ref<'untested' | 'connected' | 'error'>('untested')
const chromeTesting = ref(false)

// Search
const searchQuery = ref('')
const searchResults = ref<LeadResult[]>([])
const searching = ref(false)
const searchError = ref('')

// Audit results (main profile + related niche users)
const auditedProfile = ref<LeadResult | null>(null)
const relatedUsers = ref<LeadResult[]>([])
const showAudit = ref(false)
const auditing = ref(false)

// AI analysis
const profileAnalysis = ref<ProfileAnalysis | null>(null)
const analyzingProfile = ref(false)
const showAnalysis = ref(false)

// Website scraping
const websiteUrl = ref('')
const websiteData = ref<any>(null)
const scrapingWebsite = ref(false)
const scrapedSummary = ref('')

// Campaign creation
const newCampaignDescription = ref('')
const newCampaignPlatforms = ref<string[]>(['twitter'])
const enriching = ref(false)
const enrichmentResult = ref<CampaignEnrichment | null>(null)
const showEnrichment = ref(false)
const campaignKeywords = ref('')
const creatingCampaign = ref(false)

// Competitor tracking (in detail view)
const newCompetitorName = ref('')
const newCompetitorUrl = ref('')
const addingCompetitor = ref(false)

// Viral post tracking
const newViralPostText = ref('')
const newViralPostUrl = ref('')
const addingViralPost = ref(false)

// Campaign list/detail
const campaigns = ref<Campaign[]>([])
const loadingCampaigns = ref(false)
const selectedCampaign = ref<Campaign | null>(null)
const campaignLeads = ref<LeadResult[]>([])
const loadingCampaignDetail = ref(false)

// Campaign lead search
const searchMode = ref<'leads' | 'engagement'>('leads')
const searchingLeads = ref(false)
const customSearchKeywords = ref('')
const searchResultsPosts = ref<any[]>([])
const searchResultsProfiles = ref<any[]>([])
const engagementSuggestions = ref<any[]>([])
const showLeadSearchResults = ref(false)
const leadSearchError = ref('')

// IndexedDB cache state
const dbReady = ref(false)
const isCachedResult = ref(false)

// Add-to-campaign dropdown
const showCampaignPicker = ref<string | null>(null)

const testChromeConnection = async () => {
  chromeTesting.value = true
  chromeStatus.value = 'untested'
  try {
    const res = await $fetch<{ status: string }>(`${API_URL}/api/leadgen/health?port=${chromePort.value}`)
    chromeStatus.value = res.status === 'ok' ? 'connected' : 'error'
  } catch {
    chromeStatus.value = 'error'
  } finally {
    chromeTesting.value = false
  }
}

const searchProfile = async (forceRefresh = false) => {
  if (!searchQuery.value.trim()) return

  const username = searchQuery.value.trim()

  // Restore from cache first (unless forced refresh)
  if (!forceRefresh) {
    const cached = await getAudit(username)
    if (cached && cached.profile) {
      auditedProfile.value = cached.profile
      relatedUsers.value = cached.related_users || []
      searchResults.value = [cached.profile, ...(cached.related_users || [])]
      showAudit.value = true
      isCachedResult.value = true
      // Also restore AI analysis if cached
      const cachedAnalysis = await getAudit(username + '_analysis')
      if (cachedAnalysis) {
        profileAnalysis.value = cachedAnalysis as ProfileAnalysis
        showAnalysis.value = true
      }
    }
  }

  searching.value = true
  searchError.value = ''
  if (!forceRefresh && !profileAnalysis.value) {
    showAnalysis.value = false
  }
  try {
    const res = await $fetch<{ status: string; data: { profile: LeadResult; related_users: LeadResult[] } }>(
      `${API_URL}/api/leadgen/twitter-audit?username=${encodeURIComponent(username)}&port=${chromePort.value}`
    )
    if (res.status === 'ok' && res.data) {
      auditedProfile.value = res.data.profile
      relatedUsers.value = res.data.related_users || []
      searchResults.value = [res.data.profile, ...relatedUsers.value]
      showAudit.value = true
      isCachedResult.value = false
      saveProfile(res.data.profile)
      relatedUsers.value.forEach(u => saveProfile(u))
      saveAudit(username, {
        profile: res.data.profile,
        related_users: res.data.related_users || [],
      })
    } else if (!auditedProfile.value) {
      searchError.value = 'Profile not found'
    } else if (forceRefresh) {
      // Backend failed but we have a cached version — keep it
      isCachedResult.value = true
    }
  } catch (e: any) {
    if (!auditedProfile.value) {
      searchError.value = e?.data?.message || e?.message || 'Search failed'
    } else if (forceRefresh) {
      isCachedResult.value = true
    }
  } finally {
    searching.value = false
  }
}

const analyzeProfile = async (profile: LeadResult) => {
  analyzingProfile.value = true
  showAnalysis.value = true

  // Show cached analysis instantly
  if (!profileAnalysis.value) {
    const cached = await getAudit(profile.username + '_analysis')
    if (cached) {
      profileAnalysis.value = cached as ProfileAnalysis
    }
  }

  try {
    const res = await $fetch<{ status: string; data: ProfileAnalysis }>(
      `${API_URL}/api/leadgen/enhance-profile`,
      { method: 'POST', body: { profile } }
    )
    if (res.status === 'ok' && res.data) {
      profileAnalysis.value = res.data
      saveAudit(profile.username + '_analysis', res.data)
    }
  } catch {
    // Keep cached version if refresh fails
  } finally {
    analyzingProfile.value = false
  }
}

const scrapeWebsite = async () => {
  if (!websiteUrl.value.trim()) return

  const url = websiteUrl.value.trim()

  // Restore from cache first
  const cached = await getScrapedSite(url)
  if (cached && cached.summary) {
    websiteData.value = cached
    scrapedSummary.value = cached.summary?.slice(0, 500) || ''
  }

  scrapingWebsite.value = true
  if (!cached) {
    websiteData.value = null
    scrapedSummary.value = ''
  }
  try {
    const res = await $fetch<{ status: string; data: any }>(
      `${API_URL}/api/leadgen/scrape-url`,
      { method: 'POST', body: { url } }
    )
    if (res.status === 'ok' && res.data) {
      websiteData.value = res.data
      scrapedSummary.value = res.data.summary?.slice(0, 500) || ''
      saveScrapedSite(res.data)
    }
  } catch {
    if (!cached) {
      websiteData.value = null
      scrapedSummary.value = ''
    }
  } finally {
    scrapingWebsite.value = false
  }
}

const enrichCampaign = async () => {
  if (!newCampaignDescription.value.trim()) return
  enriching.value = true
  enrichmentResult.value = null
  showEnrichment.value = false
  try {
    const body: Record<string, any> = { description: newCampaignDescription.value }
    if (websiteData.value) {
      body.website_data = websiteData.value
    }
    const res = await $fetch<{ status: string; data: CampaignEnrichment }>(
      `${API_URL}/api/leadgen/campaign/enrich`,
      { method: 'POST', body }
    )
    if (res.status === 'ok' && res.data) {
      enrichmentResult.value = res.data
      campaignKeywords.value = res.data.keywords.join(', ')
      showEnrichment.value = true
    }
  } catch {
    // fallback
  } finally {
    enriching.value = false
  }
}

const createCampaign = async () => {
  if (!newCampaignDescription.value.trim()) return
  creatingCampaign.value = true
  try {
    const keywords = campaignKeywords.value.split(',').map(k => k.trim()).filter(Boolean)
    const body: Record<string, any> = {
      name: enrichmentResult.value?.refined_name || newCampaignDescription.value.split('.')[0].slice(0, 50),
      description: newCampaignDescription.value,
      keywords: keywords.length ? keywords : [newCampaignDescription.value],
      platforms: newCampaignPlatforms.value,
    }
    if (enrichmentResult.value) {
      body.enrichment = enrichmentResult.value
    }
    const res = await $fetch<{ status: string; data: Campaign }>(
      `${API_URL}/api/leadgen/campaigns`,
      { method: 'POST', body }
    )
    if (res.status === 'ok' && res.data) {
      campaigns.value.unshift(res.data)
      saveCampaign(res.data)
      newCampaignDescription.value = ''
      campaignKeywords.value = ''
      enrichmentResult.value = null
      showEnrichment.value = false
      websiteUrl.value = ''
      websiteData.value = null
      scrapedSummary.value = ''
      newCampaignPlatforms.value = ['twitter']
    }
  } catch {
    // fail silently
  } finally {
    creatingCampaign.value = false
  }
}

const addCompetitor = async () => {
  if (!selectedCampaign.value || !newCompetitorName.value.trim()) return
  addingCompetitor.value = true
  try {
    const res = await $fetch<{ status: string; data: any }>(
      `${API_URL}/api/leadgen/campaigns/${selectedCampaign.value.id}/competitors`,
      {
        method: 'POST',
        body: {
          name: newCompetitorName.value.trim(),
          url: newCompetitorUrl.value.trim(),
        },
      }
    )
    if (res.status === 'ok' && res.data) {
      if (!selectedCampaign.value.competitors) selectedCampaign.value.competitors = []
      selectedCampaign.value.competitors.push(res.data)
      newCompetitorName.value = ''
      newCompetitorUrl.value = ''
    }
  } catch {
    // silent
  } finally {
    addingCompetitor.value = false
  }
}

const removeCompetitor = async (competitorId: string) => {
  if (!selectedCampaign.value) return
  try {
    await $fetch(`${API_URL}/api/leadgen/campaigns/${selectedCampaign.value.id}/competitors/${competitorId}`, { method: 'DELETE' })
    selectedCampaign.value.competitors = (selectedCampaign.value.competitors || []).filter(c => c.id !== competitorId)
  } catch {
    // silent
  }
}

const addViralPost = async () => {
  if (!selectedCampaign.value || !newViralPostText.value.trim()) return
  addingViralPost.value = true
  try {
    const res = await $fetch<{ status: string; data: any }>(
      `${API_URL}/api/leadgen/campaigns/${selectedCampaign.value.id}/viral-posts`,
      {
        method: 'POST',
        body: {
          post_text: newViralPostText.value.trim(),
          post_url: newViralPostUrl.value.trim(),
        },
      }
    )
    if (res.status === 'ok' && res.data) {
      if (!selectedCampaign.value.viral_posts) selectedCampaign.value.viral_posts = []
      selectedCampaign.value.viral_posts.unshift(res.data)
      newViralPostText.value = ''
      newViralPostUrl.value = ''
    }
  } catch {
    // silent
  } finally {
    addingViralPost.value = false
  }
}

const loadCampaigns = async () => {
  loadingCampaigns.value = true
  try {
    const res = await $fetch<{ status: string; data: Campaign[] }>(`${API_URL}/api/leadgen/campaigns`)
    if (res.status === 'ok') {
      campaigns.value = res.data || []
    }
  } catch {
    // backend might not be running
  } finally {
    loadingCampaigns.value = false
  }
}

const viewCampaign = async (campaign: Campaign) => {
  selectedCampaignId.value = campaign.id
  selectedCampaign.value = campaign
  campaignLeads.value = []
  loadingCampaignDetail.value = true
  try {
    const res = await $fetch<{ status: string; data: Campaign }>(
      `${API_URL}/api/leadgen/campaigns/${campaign.id}`
    )
    if (res.status === 'ok' && res.data) {
      selectedCampaign.value = res.data
      campaignLeads.value = (res.data as any).leads || []
      saveCampaign(res.data)
    }
    // Restore cached search results for this campaign
    const cachedPosts = await getPostsByCampaign(campaign.id)
    if (cachedPosts.length > 0 && searchResultsPosts.value.length === 0) {
      searchResultsPosts.value = cachedPosts
    }
    const cachedEngagement = await getEngagementByCampaign(campaign.id)
    if (cachedEngagement.length > 0 && engagementSuggestions.value.length === 0) {
      engagementSuggestions.value = cachedEngagement
    }
    if (cachedPosts.length > 0 || cachedEngagement.length > 0) {
      showLeadSearchResults.value = true
    }
  } catch {
    // silent
  } finally {
    loadingCampaignDetail.value = false
  }
}

const backToCampaigns = () => {
  selectedCampaignId.value = null
  selectedCampaign.value = null
  campaignLeads.value = []
}

const deleteCampaign = async (id: string) => {
  try {
    await $fetch(`${API_URL}/api/leadgen/campaigns/${id}`, { method: 'DELETE' })
    campaigns.value = campaigns.value.filter(c => c.id !== id)
    if (selectedCampaignId.value === id) {
      backToCampaigns()
    }
  } catch {
    // silent
  }
}

const searchCampaignLeads = async (mode: 'leads' | 'engagement' = 'leads') => {
  if (!selectedCampaign.value) return
  searchMode.value = mode
  searchingLeads.value = true
  leadSearchError.value = ''
  showLeadSearchResults.value = false
  searchResultsPosts.value = []
  searchResultsProfiles.value = []
  engagementSuggestions.value = []
  // Parse custom keywords
  const extra = customSearchKeywords.value.split(',').map(k => k.trim()).filter(Boolean)
  try {
    const res = await $fetch<any>(
      `${API_URL}/api/leadgen/campaigns/${selectedCampaign.value.id}/search-leads`,
      {
        method: 'POST',
        body: {
          mode,
          port: chromePort.value,
          max_results: mode === 'engagement' ? 15 : 10,
          custom_keywords: extra.length ? extra : undefined,
        },
      }
    )
    if (res.status === 'ok') {
      searchResultsPosts.value = res.data.posts || []
      searchResultsProfiles.value = res.data.profiles || []
      engagementSuggestions.value = res.data.engagement_suggestions || []
      showLeadSearchResults.value = true
      // Persist to IndexedDB
      if (selectedCampaign.value) {
        savePosts(searchResultsPosts.value, selectedCampaign.value.id)
        saveEngagementSuggestions(engagementSuggestions.value, selectedCampaign.value.id)
      }
      // Refresh campaign detail so lead_count updates
      if (selectedCampaign.value && mode === 'leads') {
        const updated = await $fetch<{ status: string; data: Campaign }>(
          `${API_URL}/api/leadgen/campaigns/${selectedCampaign.value.id}`
        )
        if (updated.status === 'ok' && updated.data) {
          selectedCampaign.value = updated.data
          campaignLeads.value = (updated.data as any).leads || []
        }
      }
    }
  } catch (e: any) {
    leadSearchError.value = e?.data?.message || e?.message || 'Search failed'
  } finally {
    searchingLeads.value = false
  }
}

const addToCampaign = async (lead: LeadResult, campaignId: string) => {
  try {
    await $fetch(`${API_URL}/api/leadgen/campaigns/${campaignId}/leads`, {
      method: 'POST', body: lead
    })
    showCampaignPicker.value = null
    // Update lead count in campaign list
    const c = campaigns.value.find(c => c.id === campaignId)
    if (c) c.lead_count++
  } catch {
    // silent
  }
}

const toggleCampaignPicker = (leadId: string) => {
  showCampaignPicker.value = showCampaignPicker.value === leadId ? null : leadId
}

const statusColor = (status: string) => {
  switch (status) {
    case 'connected': return 'text-green-500'
    case 'error': return 'text-red-500'
    default: return 'text-gray-400'
  }
}

const platformIcon = (platform: string) => {
  const icons: Record<string, string> = {
    twitter: 'mdi:twitter',
    instagram: 'mdi:instagram',
    tiktok: 'mdi:music-note',
    youtube: 'mdi:youtube',
    facebook: 'mdi:facebook',
  }
  return icons[platform] || 'mdi:web'
}

const formatCount = (n: number | null) => {
  if (!n) return '—'
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return n.toString()
}

onMounted(async () => {
  dbReady.value = true
  // Restore cached campaigns from IndexedDB as fallback
  loadCampaigns()
  const cached = await getAllCampaigns()
  if (cached.length > 0 && campaigns.value.length === 0) {
    campaigns.value = cached
  }
})
</script>

<template>
  <div class="max-w-5xl mx-auto p-6">
    <header class="mb-8">
      <h1 class="text-3xl font-bold">Social Lead Gen</h1>
      <p class="text-sm opacity-60 mt-1">Find, analyze, and engage with leads using AI + Chrome DevTools</p>
    </header>

    <div class="flex gap-2 mb-6">
      <button
        @click="activeTab = 'search'"
        :class="['px-4 py-2 rounded-lg text-sm font-medium transition', activeTab === 'search' ? 'bg-blue-600 text-white' : 'bg-slate-200 dark:bg-slate-700']"
      >Search</button>
      <button
        @click="activeTab = 'campaigns'"
        :class="['px-4 py-2 rounded-lg text-sm font-medium transition', activeTab === 'campaigns' ? 'bg-blue-600 text-white' : 'bg-slate-200 dark:bg-slate-700']"
      >Campaigns</button>
    </div>

    <!-- ============ SEARCH TAB ============ -->
    <div v-if="activeTab === 'search'">
      <!-- Chrome Connection -->
      <section class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-5 mb-6">
        <h2 class="text-lg font-semibold mb-4">Chrome Connection</h2>
        <div class="flex items-center gap-3 mb-3">
          <label class="text-sm">Port:</label>
          <input
            v-model.number="chromePort"
            type="number"
            class="w-24 px-3 py-1.5 rounded border dark:bg-slate-700 dark:border-slate-600 text-sm"
            placeholder="9222"
          />
          <button
            @click="testChromeConnection"
            :disabled="chromeTesting"
            class="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {{ chromeTesting ? 'Testing...' : 'Test Connection' }}
          </button>
          <span v-if="chromeStatus !== 'untested'" :class="statusColor(chromeStatus)" class="text-sm font-medium">
            {{ chromeStatus === 'connected' ? '● Connected' : '● Failed' }}
          </span>
        </div>
      </section>

      <!-- Search -->
      <section class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-5 mb-6">
        <h2 class="text-lg font-semibold mb-4">Complete Profile Audit</h2>
        <p class="text-xs opacity-60 mb-3">Search a Twitter/X profile to get a full audit: profile analysis, related niche accounts, and AI-powered audience intelligence.</p>
        <div class="flex gap-2 mb-4">
          <input
            v-model="searchQuery"
            @keyup.enter="searchProfile"
            type="text"
            class="flex-1 px-3 py-1.5 rounded border dark:bg-slate-700 dark:border-slate-600 text-sm"
            placeholder="Twitter username (e.g. Scrapling_dev)"
          />
          <button
            @click="searchProfile"
            :disabled="searching || !searchQuery.trim()"
            class="px-4 py-1.5 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50"
          >
            {{ searching ? 'Refreshing...' : isCachedResult ? '↻ Refresh Audit' : 'Search & Audit' }}
          </button>
        </div>
        <p v-if="searchError" class="text-red-500 text-sm">{{ searchError }}</p>
      </section>

      <!-- Audit Results -->
      <section v-if="showAudit && auditedProfile" class="space-y-4 mb-6">
        <!-- Cached indicator -->
        <div v-if="isCachedResult" class="flex items-center gap-2 text-xs text-clipper-ink dark:text-white mb-1">
          <span>● Loaded from cache</span>
          <span class="opacity-50">|</span>
          <span class="text-clipper-green cursor-pointer hover:underline" @click="searchProfile(true)">Force refresh from server</span>
        </div>
        <!-- Main Profile Card -->
        <div class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-5 border-l-4 border-clipper-green">
          <div class="flex items-start gap-4">
            <img
              v-if="auditedProfile.avatar_url"
              :src="auditedProfile.avatar_url"
              :alt="auditedProfile.username"
              class="w-14 h-14 rounded-full object-cover flex-shrink-0"
            />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-base font-bold">{{ auditedProfile.display_name || auditedProfile.username }}</span>
                <span v-if="auditedProfile.is_verified" class="text-clipper-green text-xs">✓</span>
                <span class="text-sm opacity-50">@{{ auditedProfile.username }}</span>
                <span class="px-1.5 py-0.5 text-xs rounded bg-blue-900/30 text-clipper-ink/60 dark:text-white/60 border border-blue-800/30 ml-auto">Primary</span>
              </div>
              <p v-if="auditedProfile.bio" class="text-sm opacity-70 mt-1">{{ auditedProfile.bio }}</p>
              <div class="flex gap-4 mt-2 text-sm">
                <span v-if="auditedProfile.follower_count !== null" class="font-medium">{{ formatCount(auditedProfile.follower_count) }} <span class="font-normal opacity-60">followers</span></span>
                <span v-if="auditedProfile.following_count !== null" class="font-medium">{{ formatCount(auditedProfile.following_count) }} <span class="font-normal opacity-60">following</span></span>
              </div>
              <div class="flex gap-2 mt-3">
                <a :href="auditedProfile.profile_url" target="_blank"
                  class="px-3 py-1 text-xs bg-slate-200 dark:bg-slate-700 rounded hover:bg-slate-300 dark:hover:bg-slate-600 transition">View Profile</a>
                <button @click="analyzeProfile(auditedProfile)"
                  class="px-3 py-1 text-xs bg-clipper-green text-white rounded hover:opacity-90 transition disabled:opacity-50"
                  :disabled="analyzingProfile">
                  {{ analyzingProfile ? 'Analyzing...' : 'AI Audience Analysis' }}
                </button>
                <button @click="toggleCampaignPicker(auditedProfile.id)"
                  class="px-3 py-1 text-xs bg-amber-600 text-white rounded hover:bg-amber-700 transition relative">
                  Add to Campaign
                  <div v-if="showCampaignPicker === auditedProfile.id"
                    @click.stop
                    class="absolute top-full left-0 mt-1 w-56 bg-white dark:bg-[#0F172A] border border-clipper-ink/08 dark:border-white/10 rounded-lg shadow-xl z-50 max-h-48 overflow-y-auto">
                    <div v-if="campaigns.length === 0" class="px-3 py-2 text-xs opacity-50">No campaigns yet</div>
                    <button v-for="c in campaigns" :key="c.id"
                      @click.stop="addToCampaign(auditedProfile, c.id)"
                      class="w-full text-left px-3 py-2 text-xs hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-2">
                      <span>{{ c.name }}</span>
                      <span class="ml-auto opacity-40">{{ c.lead_count }} leads</span>
                    </button>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- AI Profile Analysis -->
        <div v-if="showAnalysis && profileAnalysis" class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-5 border-l-4 border-clipper-ink/12 dark:border-white/10">
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-semibold text-clipper-ink dark:text-white">AI Audience Intelligence</h3>
            <button @click="showAnalysis = false" class="text-xs opacity-50 hover:opacity-100">Close</button>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 class="text-xs font-semibold text-clipper-ink dark:text-white mb-1">Audience Demographics</h4>
              <p class="text-xs opacity-80">{{ profileAnalysis.audience_demographics }}</p>
            </div>
            <div>
              <h4 class="text-xs font-semibold text-green-400 mb-1">Steal Audience Strategy</h4>
              <p class="text-xs opacity-80">{{ profileAnalysis.steal_audience_strategy }}</p>
            </div>
            <div>
              <h4 class="text-xs font-semibold text-cyan-400 mb-1">Recommended Outreach</h4>
              <p class="text-xs opacity-80">{{ profileAnalysis.recommended_outreach }}</p>
            </div>
            <div v-if="profileAnalysis.content_themes.length">
              <h4 class="text-xs font-semibold text-clipper-green mb-1">Content Themes</h4>
              <div class="flex flex-wrap gap-1">
                <span v-for="t in profileAnalysis.content_themes" :key="t" class="px-1.5 py-0.5 text-xs rounded bg-blue-900/30 text-clipper-ink/60 dark:text-white/60 border border-blue-800/30">{{ t }}</span>
              </div>
            </div>
            <div v-if="profileAnalysis.competitor_overlap.length">
              <h4 class="text-xs font-semibold text-amber-400 mb-1">Competitor Overlap</h4>
              <div class="flex flex-wrap gap-1">
                <span v-for="c in profileAnalysis.competitor_overlap" :key="c" class="px-1.5 py-0.5 text-xs rounded bg-amber-900/30 text-amber-300 border border-amber-800/30">{{ c }}</span>
              </div>
            </div>
            <div v-if="profileAnalysis.intent_signals.length">
              <h4 class="text-xs font-semibold text-pink-400 mb-1">Buying Intent Signals</h4>
              <ul class="text-xs opacity-80 list-disc list-inside">
                <li v-for="s in profileAnalysis.intent_signals" :key="s">{{ s }}</li>
              </ul>
            </div>
          </div>
        </div>
        <div v-else-if="analyzingProfile" class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-5 flex items-center gap-2 text-sm opacity-60">
          <span class="inline-block w-3 h-3 border-2 border-clipper-ink/12 dark:border-white/10 border-t-transparent rounded-full animate-spin"></span>
          Analyzing profile with AI...
        </div>

        <!-- Related Niche Users -->
        <div v-if="relatedUsers.length">
          <div class="flex items-center gap-2 mb-3">
            <h3 class="font-semibold">Related Niche Accounts</h3>
            <span class="text-xs opacity-50">({{ relatedUsers.length }} found)</span>
          </div>
          <div class="space-y-2">
            <div v-for="lead in relatedUsers" :key="lead.id"
              class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-3 flex items-center gap-3 border border-clipper-ink/08 dark:border-white/08/30">
              <img v-if="lead.avatar_url" :src="lead.avatar_url" class="w-9 h-9 rounded-full flex-shrink-0" />
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1.5">
                  <Icon :name="platformIcon(lead.platform)" class="text-clipper-green" size="14" />
                  <span class="text-sm font-medium">{{ lead.display_name || lead.username }}</span>
                  <span v-if="lead.is_verified" class="text-clipper-green text-xs">✓</span>
                  <span class="text-xs opacity-50">@{{ lead.username }}</span>
                </div>
                <p v-if="lead.bio" class="text-xs opacity-60 mt-0.5 line-clamp-1">{{ lead.bio }}</p>
              </div>
              <div class="flex items-center gap-1.5 flex-shrink-0">
                <a v-if="lead.profile_url" :href="lead.profile_url" target="_blank"
                  class="px-2 py-1 text-xs bg-slate-200 dark:bg-slate-700 rounded hover:bg-slate-300 dark:hover:bg-slate-600 transition">View</a>
                <button @click="toggleCampaignPicker(lead.id)"
                  class="px-2 py-1 text-xs bg-amber-600 text-white rounded hover:bg-amber-700 transition relative">
                  +
                  <div v-if="showCampaignPicker === lead.id"
                    @click.stop
                    class="absolute top-full right-0 mt-1 w-52 bg-white dark:bg-[#0F172A] border border-clipper-ink/08 dark:border-white/10 rounded-lg shadow-xl z-50 max-h-40 overflow-y-auto">
                    <div v-if="campaigns.length === 0" class="px-3 py-2 text-xs opacity-50">No campaigns</div>
                    <button v-for="c in campaigns" :key="c.id"
                      @click.stop="addToCampaign(lead, c.id)"
                      class="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-2">
                      <span>{{ c.name }}</span>
                    </button>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- ============ CAMPAIGNS TAB ============ -->
    <div v-if="activeTab === 'campaigns'">
      <!-- Campaign Detail View -->
      <div v-if="selectedCampaign">
        <button @click="backToCampaigns" class="text-sm text-clipper-green hover:text-clipper-ink/60 dark:text-white/60 mb-4 flex items-center gap-1">
          ← Back to campaigns
        </button>

        <div class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-6 mb-6">
          <div class="flex items-start justify-between mb-4">
            <div>
              <h2 class="text-xl font-bold">{{ selectedCampaign.name }}</h2>
              <p class="text-sm opacity-60 mt-1">
                <span v-for="(p, i) in (selectedCampaign.platforms || [selectedCampaign.platform])" :key="p">
                  {{ i > 0 ? ', ' : '' }}<Icon :name="platformIcon(p)" size="14" class="inline" /> {{ p === 'twitter' ? 'X' : p }}
                </span>
                • {{ selectedCampaign.lead_count }} leads
              </p>
            </div>
            <span class="px-2 py-0.5 text-xs rounded bg-green-900/30 text-green-300 border border-green-800/30">{{ selectedCampaign.status }}</span>
          </div>

          <p v-if="selectedCampaign.description" class="text-sm opacity-70 mb-4">{{ selectedCampaign.description }}</p>

          <div v-if="selectedCampaign.keywords.length" class="mb-4">
            <h3 class="text-sm font-semibold mb-1.5">Keywords</h3>
            <div class="flex flex-wrap gap-1.5">
              <span v-for="kw in selectedCampaign.keywords" :key="kw"
                class="px-2 py-0.5 text-xs rounded bg-blue-900/30 text-clipper-ink/60 dark:text-white/60 border border-blue-800/30">{{ kw }}</span>
            </div>
          </div>

          <div v-if="selectedCampaign.competitor_keywords.length" class="mb-4">
            <h3 class="text-sm font-semibold mb-1.5">Competitors</h3>
            <div class="flex flex-wrap gap-1.5">
              <span v-for="kw in selectedCampaign.competitor_keywords" :key="kw"
                class="px-2 py-0.5 text-xs rounded bg-red-900/30 text-red-300 border border-red-800/30">{{ kw }}</span>
            </div>
          </div>

          <div v-if="selectedCampaign.target_audience" class="mb-4">
            <h3 class="text-sm font-semibold mb-1 text-clipper-ink dark:text-white">Target Audience</h3>
            <p class="text-sm opacity-80">{{ selectedCampaign.target_audience }}</p>
          </div>

          <div v-if="selectedCampaign.intent_queries.length" class="mb-4">
            <h3 class="text-sm font-semibold mb-1.5 text-amber-400">Intent-Based Search Queries</h3>
            <div class="space-y-1">
              <div v-for="(q, i) in selectedCampaign.intent_queries" :key="i"
                class="text-xs opacity-70 font-mono bg-neutral-100 dark:bg-neutral-800 rounded px-2 py-1">"{{ q }}"</div>
            </div>
          </div>

          <div v-if="selectedCampaign.pain_points.length" class="mb-4">
            <h3 class="text-sm font-semibold mb-1.5 text-red-400">Pain Points</h3>
            <div class="flex flex-wrap gap-1.5">
              <span v-for="p in selectedCampaign.pain_points" :key="p"
                class="px-2 py-0.5 text-xs rounded bg-red-900/30 text-red-300 border border-red-800/30">{{ p }}</span>
            </div>
          </div>

          <div v-if="selectedCampaign.steal_audience_angle" class="mb-4">
            <h3 class="text-sm font-semibold mb-1 text-green-400">Audience Capture Strategy</h3>
            <p class="text-sm opacity-80">{{ selectedCampaign.steal_audience_angle }}</p>
          </div>

          <div v-if="selectedCampaign.value_proposition" class="mb-4">
            <h3 class="text-sm font-semibold mb-1 text-cyan-400">Value Proposition</h3>
            <p class="text-sm opacity-80">{{ selectedCampaign.value_proposition }}</p>
          </div>

          <div v-if="selectedCampaign.viral_content_angles?.length" class="mb-4">
            <h3 class="text-sm font-semibold mb-1.5 text-pink-400">Viral Content Angles</h3>
            <div class="flex flex-wrap gap-1.5">
              <span v-for="v in selectedCampaign.viral_content_angles" :key="v"
                class="px-2 py-0.5 text-xs rounded bg-pink-900/30 text-pink-300 border border-pink-800/30">{{ v }}</span>
            </div>
          </div>

          <!-- Active Competitor Tracking -->
          <div class="border-t dark:border-clipper-ink/08 dark:border-white/08 border-slate-300 pt-4 mt-4">
            <h3 class="font-semibold mb-3 flex items-center gap-2">
              Tracked Competitors
              <span class="text-xs opacity-50">({{ selectedCampaign.competitors?.length || 0 }})</span>
            </h3>
            <div v-if="selectedCampaign.competitors?.length" class="space-y-2 mb-3">
              <div v-for="comp in selectedCampaign.competitors" :key="comp.id"
                class="flex items-start gap-2 bg-red-900/10 border border-red-800/20 rounded p-2.5">
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-1.5">
                    <span class="text-sm font-medium text-red-300">{{ comp.name }}</span>
                    <a v-if="comp.url" :href="comp.url" target="_blank" class="text-xs text-clipper-green">↗</a>
                  </div>
                  <div v-if="comp.analysis" class="text-xs opacity-70 mt-1 space-y-0.5">
                    <p v-if="comp.analysis.content_strategy"><span class="text-amber-400">Strategy:</span> {{ comp.analysis.content_strategy }}</p>
                    <p v-if="comp.analysis.steal_play"><span class="text-green-400">Steal play:</span> {{ comp.analysis.steal_play }}</p>
                    <p v-if="comp.analysis.estimated_reach"><span class="text-clipper-ink dark:text-white">Reach:</span> {{ comp.analysis.estimated_reach }}</p>
                    <div v-if="comp.analysis.likely_platforms?.length" class="flex gap-1 mt-1">
                      <span v-for="p in comp.analysis.likely_platforms" :key="p"
                        class="px-1 py-0.5 text-xs rounded bg-slate-700/50">{{ p }}</span>
                    </div>
                  </div>
                  <p v-if="comp.notes" class="text-xs italic opacity-50 mt-1">{{ comp.notes }}</p>
                </div>
                <button @click="removeCompetitor(comp.id)" class="text-xs text-red-400 hover:text-red-300 flex-shrink-0">✕</button>
              </div>
            </div>
            <div class="flex gap-2">
              <input v-model="newCompetitorName" type="text"
                class="flex-1 px-2 py-1 rounded border dark:bg-slate-700 dark:border-slate-600 text-xs"
                placeholder="Competitor name" />
              <input v-model="newCompetitorUrl" type="text"
                class="w-36 px-2 py-1 rounded border dark:bg-slate-700 dark:border-slate-600 text-xs"
                placeholder="URL (optional)" />
              <button @click="addCompetitor" :disabled="addingCompetitor || !newCompetitorName.trim()"
                class="px-2 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700 disabled:opacity-50 flex-shrink-0">
                {{ addingCompetitor ? '...' : '+ Track' }}
              </button>
            </div>
          </div>

          <!-- Viral Post Monitor -->
          <div class="border-t dark:border-clipper-ink/08 dark:border-white/08 border-slate-300 pt-4 mt-4">
            <h3 class="font-semibold mb-3 flex items-center gap-2">
              Viral Post Monitor
              <span class="text-xs opacity-50">({{ selectedCampaign.viral_posts?.length || 0 }})</span>
            </h3>
            <div v-if="selectedCampaign.viral_posts?.length" class="space-y-2 mb-3">
              <div v-for="vp in selectedCampaign.viral_posts" :key="vp.id"
                class="bg-pink-900/10 border border-pink-800/20 rounded p-2.5">
                <p class="text-xs opacity-80 mb-1">{{ vp.post_text?.slice(0, 200) }}</p>
                <div v-if="vp.analysis" class="text-xs opacity-70 space-y-1 mt-1.5 pt-1.5 border-t border-pink-800/20">
                  <p v-if="vp.analysis.viral_hook"><span class="text-pink-400">Hook:</span> {{ vp.analysis.viral_hook }}</p>
                  <p v-if="vp.analysis.replication_angle"><span class="text-green-400">Replicate:</span> {{ vp.analysis.replication_angle }}</p>
                  <p v-if="vp.analysis.suggested_reply"><span class="text-clipper-green">Reply:</span> {{ vp.analysis.suggested_reply }}</p>
                  <div v-if="vp.analysis.improved_version" class="mt-2 bg-green-900/20 border border-green-700/30 rounded p-2">
                    <span class="text-green-400 font-semibold">Improved version:</span>
                    <p class="text-green-200/90 mt-0.5">{{ vp.analysis.improved_version }}</p>
                  </div>
                  <div v-if="vp.analysis.format" class="mt-1 flex gap-1">
                    <span class="px-1 py-0.5 text-xs rounded bg-pink-900/30 text-pink-300">{{ vp.analysis.format }}</span>
                  </div>
                </div>
                <a v-if="vp.post_url" :href="vp.post_url" target="_blank" class="text-xs text-clipper-green mt-1 inline-block">View Post →</a>
              </div>
            </div>
            <div class="space-y-2">
              <textarea v-model="newViralPostText" rows="2"
                class="w-full px-2 py-1 rounded border dark:bg-slate-700 dark:border-slate-600 text-xs resize-none"
                placeholder="Paste a post text here to analyze why it's viral..."></textarea>
              <div class="flex gap-2">
                <input v-model="newViralPostUrl" type="text"
                  class="flex-1 px-2 py-1 rounded border dark:bg-slate-700 dark:border-slate-600 text-xs"
                  placeholder="Post URL (optional)" />
                <button @click="addViralPost" :disabled="addingViralPost || !newViralPostText.trim()"
                  class="px-2 py-1 bg-pink-600 text-white rounded text-xs hover:bg-pink-700 disabled:opacity-50">
                  {{ addingViralPost ? 'Analyzing...' : 'AI Analyze' }}
                </button>
              </div>
            </div>
          </div>

          <!-- Find Leads / Engagement CTA -->
          <div class="border-t dark:border-clipper-ink/08 dark:border-white/08 border-slate-300 pt-4 mt-4 space-y-2">
            <div class="flex items-center gap-2">
              <button @click="searchCampaignLeads('leads')"
                :disabled="searchingLeads"
                class="flex-1 px-4 py-2.5 bg-clipper-green">
                <span v-if="searchingLeads && searchMode === 'leads'" class="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                {{ searchingLeads && searchMode === 'leads' ? 'GPT generating best queries...' : campaignLeads.length === 0 ? '🎯 Find Leads — Search & Auto-Add' : '🎯 Find More Leads' }}
              </button>
              <button @click="searchCampaignLeads('engagement')"
                :disabled="searchingLeads"
                class="flex-1 px-4 py-2.5 bg-clipper-green">
                <span v-if="searchingLeads && searchMode === 'engagement'" class="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                {{ searchingLeads && searchMode === 'engagement' ? 'GPT finding conversations...' : '💬 Find Posts to Engage With' }}
              </button>
              <span v-if="showLeadSearchResults && searchResultsPosts.length" title="Cached results loaded from IndexedDB" class="text-xs text-clipper-ink dark:text-white flex-shrink-0">● cached</span>
            </div>
            <p v-if="leadSearchError" class="text-red-500 text-xs mt-2">{{ leadSearchError }}</p>
            <div class="flex gap-2">
              <input v-model="customSearchKeywords" type="text"
                class="flex-1 px-2.5 py-1.5 rounded border dark:bg-slate-700 dark:border-slate-600 text-xs"
                placeholder="Extra keywords (comma-separated) — combined with AI-generated ones"
                @keyup.enter="searchCampaignLeads(searchMode)" />
              <button @click="customSearchKeywords = ''" v-if="customSearchKeywords"
                class="px-2 text-xs opacity-50 hover:opacity-100">✕</button>
            </div>
          </div>
        </div>

        <!-- Lead Search Results (Posts + Profiles) -->
        <section v-if="showLeadSearchResults" class="mb-6 space-y-6">
          <div v-if="searchMode === 'engagement'" class="flex items-center gap-2 mb-3 px-1">
            <span class="text-xs font-semibold text-teal-400 bg-teal-900/20 px-2 py-0.5 rounded">Engagement Mode</span>
            <span class="text-xs opacity-60">GPT optimized queries to find conversations to join, not leads to collect</span>
          </div>
          <div v-if="searchResultsPosts.some((p: any) => p._gpt_generated)" class="bg-neutral-100 dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-lg p-3 text-xs text-clipper-ink/60 dark:text-white/60 mb-3 flex items-center gap-2">
            <Icon name="mdi:robot-outline" size="16" />
            <span>Real-time search returned no results. These AI-generated leads are based on your campaign context — scored and qualified by GPT.</span>
          </div>
          <!-- Posts with Engagement Suggestions -->
          <div v-if="searchResultsPosts.length">
            <h2 class="text-lg font-semibold mb-3">{{ searchMode === 'engagement' ? 'Conversations to Join' : 'Posts Found' }} ({{ searchResultsPosts.length }})</h2>
            <div v-for="(post, i) in searchResultsPosts" :key="i"
              class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-4 mb-3 border-l-4 border-clipper-ink/12 dark:border-white/10">
              <div class="flex items-start gap-3">
                <img v-if="post.avatar_url" :src="post.avatar_url" class="w-9 h-9 rounded-full flex-shrink-0" />
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-1.5 mb-1 flex-wrap">
                    <span class="text-sm font-medium">{{ post.display_name || post.username }}</span>
                    <span class="text-xs opacity-50">@{{ post.username }}</span>
                    <!-- Qualification Badge -->
                    <span v-if="post.qualification"
                      :class="['px-1.5 py-0.5 text-[10px] rounded font-semibold ml-auto',
                        post.qualification.score >= 8 ? 'bg-green-900/40 text-green-300' :
                        post.qualification.score >= 5 ? 'bg-amber-900/40 text-amber-300' :
                        'bg-neutral-100 dark:bg-neutral-800 text-clipper-ink/60 dark:text-white/60']">
                      {{ post.qualification.score }}/10 · {{ post.qualification.classification?.replace('_', ' ') }}
                    </span>
                    <span v-if="post._gpt_generated"
                      class="px-1 py-0.5 text-[10px] rounded bg-clipper-green/10 text-clipper-ink/60 dark:text-white/60">AI generated</span>
                  </div>
                  <p v-if="post.qualification?.reason" class="text-[11px] opacity-50 italic mb-1">{{ post.qualification.reason }}</p>
                  <p class="text-sm opacity-80 mb-2">{{ post.post_text || post.text }}</p>
                  <a v-if="post.post_url" :href="post.post_url" target="_blank"
                    class="text-xs text-clipper-green hover:text-clipper-ink/60 dark:text-white/60">View Post →</a>
                </div>
              </div>
              <!-- GPT Engagement Suggestion -->
              <div v-if="engagementSuggestions[i]" class="mt-3 pt-3 border-t dark:border-clipper-ink/08 dark:border-white/08 border-slate-300">
                <div class="flex items-center gap-1.5 mb-1.5">
                  <span class="text-xs font-semibold text-clipper-ink dark:text-white">AI Engagement Suggestion</span>
                  <Icon name="mdi:robot-outline" class="text-clipper-ink dark:text-white" size="14" />
                </div>
                <div class="text-xs opacity-80 whitespace-pre-wrap bg-clipper-green/[0.04] rounded p-2.5 border border-clipper-ink/08 dark:border-white/08">
                  {{ engagementSuggestions[i] }}
                </div>
              </div>
            </div>
          </div>

          <!-- Profiles Found -->
          <div v-if="searchResultsProfiles.length && searchMode === 'leads'">
            <h2 class="text-lg font-semibold mb-3">Profiles Added ({{ searchResultsProfiles.length }})</h2>
            <div v-for="lead in searchResultsProfiles" :key="lead.id"
              class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-3 flex items-center gap-3 border border-clipper-ink/08 dark:border-white/08/30">
              <img v-if="lead.avatar_url" :src="lead.avatar_url" class="w-9 h-9 rounded-full flex-shrink-0" />
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1.5">
                  <Icon :name="platformIcon(lead.platform)" class="text-clipper-green" size="14" />
                  <span class="text-sm font-medium">{{ lead.display_name || lead.username }}</span>
                  <span class="text-xs opacity-50">@{{ lead.username }}</span>
                </div>
                <p v-if="lead.bio" class="text-xs opacity-60 mt-0.5 line-clamp-1">{{ lead.bio }}</p>
              </div>
              <a v-if="lead.profile_url" :href="lead.profile_url" target="_blank"
                class="text-xs text-clipper-green hover:text-clipper-ink/60 dark:text-white/60 flex-shrink-0">View</a>
            </div>
          </div>

          <div v-if="!searchResultsPosts.length && !searchingLeads" class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-6 text-center text-sm opacity-50">
            {{ searchMode === 'engagement' ? 'No conversations found. Try again or check Chrome connection.' : 'No results found. Try different keywords or check Chrome connection.' }}
          </div>
        </section>

        <!-- Campaign Leads -->
        <section>
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-lg font-semibold">Leads ({{ campaignLeads.length }})</h2>
            <button v-if="campaignLeads.length > 0" @click="searchCampaignLeads('leads')"
              :disabled="searchingLeads"
              class="px-3 py-1.5 text-xs bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50 transition flex items-center gap-1">
              <span v-if="searchingLeads" class="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              Refresh
            </button>
          </div>
          <div v-if="loadingCampaignDetail" class="text-sm opacity-50 py-4">Loading leads...</div>
          <div v-else-if="campaignLeads.length">
            <div v-for="lead in campaignLeads" :key="lead.id"
              class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-4 mb-2 flex gap-3 items-start">
              <img v-if="lead.avatar_url" :src="lead.avatar_url" class="w-10 h-10 rounded-full flex-shrink-0" />
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1.5">
                  <Icon :name="platformIcon(lead.platform)" class="text-clipper-green" size="14" />
                  <span class="text-sm font-medium">{{ lead.display_name || lead.username }}</span>
                  <span class="text-xs opacity-50">@{{ lead.username }}</span>
                </div>
                <p v-if="lead.bio" class="text-xs opacity-60 mt-0.5 line-clamp-1">{{ lead.bio }}</p>
                <div class="flex gap-3 mt-1.5 text-xs opacity-40">
                  <span v-if="lead.follower_count !== null">{{ formatCount(lead.follower_count) }} followers</span>
                  <span v-if="lead.intent_score">Intent: {{ lead.intent_score }}</span>
                </div>
              </div>
              <a v-if="lead.profile_url" :href="lead.profile_url" target="_blank"
                class="text-xs text-clipper-green hover:text-clipper-ink/60 dark:text-white/60 flex-shrink-0">View</a>
            </div>
          </div>
          <p v-else class="text-sm opacity-50 text-center py-6">No leads yet. Click "Find Leads" above to search and auto-add from the campaign's keywords.</p>
        </section>
      </div>

      <!-- Campaign List View -->
      <div v-else>
        <section class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-6 mb-6">
          <h2 class="text-lg font-semibold mb-4">Create Campaign</h2>
          <p class="text-xs opacity-60 mb-3">Describe what you offer — AI will generate keywords, audience analysis, and search strategies.</p>

          <div class="space-y-3">
            <textarea
              v-model="newCampaignDescription"
              rows="3"
              class="w-full px-3 py-1.5 rounded border dark:bg-slate-700 dark:border-slate-600 text-sm resize-none"
              placeholder="Describe what you offer, your target audience, and what problem you solve. e.g. 'I build AI chatbots for SaaS companies that handle customer support tickets automatically...'"
            ></textarea>

            <div>
              <label class="text-xs font-medium opacity-70 block mb-1.5">Platforms to scan</label>
              <div class="flex flex-wrap gap-3">
                <label v-for="p in ['twitter', 'instagram', 'tiktok', 'youtube', 'facebook']" :key="p"
                  class="flex items-center gap-1.5 text-sm cursor-pointer">
                  <input type="checkbox" :value="p" v-model="newCampaignPlatforms"
                    class="rounded dark:bg-slate-700 border-slate-500" />
                  <span class="capitalize">{{ p === 'twitter' ? 'Twitter/X' : p }}</span>
                </label>
              </div>
            </div>

            <!-- Website Scraping -->
            <details class="text-sm">
              <summary class="cursor-pointer text-clipper-green hover:text-clipper-ink/60 dark:text-white/60 font-medium">+ Add website URL for richer AI analysis</summary>
              <div class="mt-2 space-y-2">
                <div class="flex gap-2">
                  <input v-model="websiteUrl" type="url"
                    class="flex-1 px-3 py-1.5 rounded border dark:bg-slate-700 dark:border-slate-600 text-sm"
                    placeholder="https://yourwebsite.com"
                    @keyup.enter="scrapeWebsite" />
                  <button @click="scrapeWebsite" :disabled="scrapingWebsite || !websiteUrl.trim()"
                    class="px-3 py-1.5 bg-cyan-600 text-white rounded text-sm hover:bg-cyan-700 disabled:opacity-50">
                    {{ scrapingWebsite ? 'Scraping...' : 'Scrape' }}
                  </button>
                </div>
                <div v-if="scrapedSummary" class="text-xs opacity-70 bg-cyan-900/10 border border-cyan-800/20 rounded p-2 space-y-1">
                  <div><span class="font-semibold text-cyan-400">Scraped:</span> {{ scrapedSummary }}</div>
                  <div v-if="websiteData?.images?.length" class="flex gap-2 flex-wrap pt-1">
                    <a v-for="img in websiteData.images.slice(0, 4)" :key="img.src" :href="img.src" target="_blank"
                      class="inline-block w-14 h-14 rounded overflow-hidden border border-cyan-800/30 hover:border-cyan-500 transition">
                      <img :src="img.src" :alt="img.alt" class="w-full h-full object-cover" loading="lazy" />
                    </a>
                    <span v-if="websiteData.images.length > 4" class="text-xs opacity-50 self-center">+{{ websiteData.images.length - 4 }}</span>
                  </div>
                  <div v-if="websiteData?.videos?.length" class="flex gap-2 flex-wrap pt-1">
                    <a v-for="v in websiteData.videos" :key="v.src" :href="v.src" target="_blank"
                      class="px-1.5 py-0.5 text-xs rounded bg-cyan-900/30 text-cyan-300">▶ {{ v.type }}</a>
                  </div>
                </div>
                <div v-if="websiteData?.error" class="text-xs text-red-400">{{ websiteData.error }}</div>
              </div>
            </details>

            <button
              @click="enrichCampaign"
              :disabled="enriching || !newCampaignDescription.trim()"
              class="w-full px-4 py-2 bg-clipper-green text-white rounded text-sm hover:opacity-90 disabled:opacity-50 transition"
            >
              {{ enriching ? 'Analyzing with AI...' : 'AI-Generate Campaign Strategy' }}
            </button>

            <div v-if="showEnrichment && enrichmentResult" class="border border-clipper-ink/08 dark:border-white/08 rounded-lg p-4 space-y-3 bg-clipper-green/[0.04]">
              <div class="flex items-center gap-2">
                <span class="text-sm font-semibold text-clipper-ink dark:text-white">AI Campaign Strategy</span>
                <span class="text-xs opacity-50">refine below then create</span>
              </div>

              <div>
                <label class="text-xs text-clipper-ink dark:text-white block mb-1">Suggested Name</label>
                <p class="text-sm font-medium">{{ enrichmentResult.refined_name }}</p>
              </div>

              <div>
                <label class="text-xs text-clipper-ink dark:text-white block mb-1">Keywords</label>
                <input v-model="campaignKeywords" type="text"
                  class="w-full px-2 py-1 rounded border dark:bg-slate-700 dark:border-slate-600 text-sm"
                  placeholder="Comma-separated keywords" />
              </div>

              <div>
                <label class="text-xs text-amber-400 block mb-1">Competitor Keywords</label>
                <div class="flex flex-wrap gap-1">
                  <span v-for="kw in enrichmentResult.competitor_keywords" :key="kw"
                    class="px-1.5 py-0.5 text-xs rounded bg-red-900/30 text-red-300">{{ kw }}</span>
                </div>
              </div>

              <div>
                <label class="text-xs text-green-400 block mb-1">Target Audience</label>
                <p class="text-sm opacity-80">{{ enrichmentResult.target_audience }}</p>
              </div>

              <div>
                <label class="text-xs text-clipper-green block mb-1">Audience Capture Strategy</label>
                <p class="text-xs opacity-80">{{ enrichmentResult.steal_audience_angle }}</p>
              </div>

              <button @click="createCampaign" :disabled="creatingCampaign || !campaignKeywords.trim()"
                class="w-full px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50 transition">
                {{ creatingCampaign ? 'Creating...' : 'Create Campaign' }}
              </button>
            </div>

            <div v-if="!showEnrichment">
              <input v-model="campaignKeywords" type="text"
                class="w-full px-3 py-1.5 rounded border dark:bg-slate-700 dark:border-slate-600 text-sm mb-2"
                placeholder="Or type keywords manually (comma-separated)" />
              <button @click="createCampaign" :disabled="creatingCampaign || !newCampaignDescription.trim()"
                class="w-full px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50 transition">
                {{ creatingCampaign ? 'Creating...' : 'Create Campaign Directly' }}
              </button>
            </div>
          </div>
        </section>

        <section>
          <h2 class="text-lg font-semibold mb-3">Your Campaigns</h2>
          <div v-if="loadingCampaigns" class="text-sm opacity-50 py-4">Loading campaigns...</div>
          <div v-else-if="campaigns.length" class="space-y-3">
            <div v-for="c in campaigns" :key="c.id"
              class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-4 hover:ring-1 hover:border-clipper-ink/16 dark:hover:border-white/15 cursor-pointer transition"
              @click="viewCampaign(c)">
              <div class="flex items-start justify-between">
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <div class="flex -space-x-1">
                      <Icon v-for="p in (c.platforms || [c.platform]).slice(0, 3)" :key="p" :name="platformIcon(p)" class="text-clipper-green" size="16" />
                      <span v-if="(c.platforms || [c.platform]).length > 3" class="text-[10px] opacity-50 ml-1">+{{ (c.platforms || [c.platform]).length - 3 }}</span>
                    </div>
                    <span class="font-semibold">{{ c.name }}</span>
                    <span class="px-1.5 py-0.5 text-xs rounded bg-green-900/30 text-green-300 border border-green-800/30">{{ c.status }}</span>
                  </div>
                  <p class="text-xs opacity-60 mt-1 line-clamp-1">{{ c.description }}</p>
                  <div class="flex gap-3 mt-2 text-xs opacity-50">
                    <span>{{ c.keywords.length }} keywords</span>
                    <span>{{ c.lead_count }} leads</span>
                    <span>{{ new Date(c.created_at).toLocaleDateString() }}</span>
                  </div>
                  <div class="flex flex-wrap gap-1 mt-1.5">
                    <span v-for="kw in c.keywords.slice(0, 5)" :key="kw"
                      class="px-1.5 py-0.5 text-xs rounded bg-neutral-100 dark:bg-neutral-800 text-clipper-ink dark:text-white">{{ kw }}</span>
                    <span v-if="c.keywords.length > 5" class="px-1.5 py-0.5 text-xs rounded bg-neutral-100 dark:bg-neutral-800 text-clipper-ink/60 dark:text-white/60">+{{ c.keywords.length - 5 }}</span>
                  </div>
                </div>
                <button @click.stop="deleteCampaign(c.id)"
                  class="text-xs text-red-400 hover:text-red-300 ml-2 flex-shrink-0">✕</button>
              </div>
            </div>
          </div>
          <p v-else class="text-sm opacity-50 text-center py-8">No campaigns yet. Describe what you offer above and let AI build your strategy.</p>
        </section>
      </div>
    </div>
  </div>
</template>
