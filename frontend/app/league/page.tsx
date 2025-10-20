'use client'

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  FunnelIcon,
  ArrowPathIcon,
  SparklesIcon
} from '@heroicons/react/24/outline'
import { useRouter } from 'next/navigation'
import { BasePage } from '../../components/layout/BasePage'
import { NewsArticleCard } from '../../components/league/NewsArticleCard'
import { InjuriesTracker } from '../../components/league/InjuriesTracker'
import { TransactionsQuickFeed } from '../../components/league/TransactionsQuickFeed'
import { api } from '../../lib/api'

interface NewsArticle {
  id: string
  title: string
  summary: string
  content: string
  category: string
  date: string
  sourceCount: number
  tags: string[]
  imageUrl?: string
  sourceUrl?: string
}

const CATEGORIES = [
  { id: 'all', label: 'All News', icon: null },
  { id: 'transactions', label: 'Transactions', icon: null },
  { id: 'injuries', label: 'Injuries', icon: null },
  { id: 'rumors', label: 'Rumors', icon: null },
  { id: 'atlantic', label: 'Atlantic Division', icon: null },
]

const ATLANTIC_TEAMS = ['MTL', 'TOR', 'BOS', 'BUF', 'OTT', 'DET', 'FLA', 'TBL']

export default function LeaguePage() {
  const router = useRouter()
  const [articles, setArticles] = useState<NewsArticle[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    fetchArticles()
  }, [])

  const fetchArticles = async () => {
    setLoading(true)
    try {
      // Fetch synthesized multi-source articles (primary content)
      const synthesizedArticles = await api.getSynthesizedArticles(undefined, 7)
      
      // Fetch daily article
      const dailyArticle = await api.getDailyArticle()
      
      // Fetch transactions
      const transactions = await api.getTransactions(168) // Last week
      
      // Fetch games for context
      const games = await api.getRecentGames(7)
      
      // Generate article cards from real data
      const generatedArticles: NewsArticle[] = []
      
      // Add synthesized multi-source articles FIRST (highest priority)
      // Only filter OUT transaction summaries - injury articles are newsworthy!
      synthesizedArticles.forEach((article: any) => {
        const category = determineCategory(article.title, article.summary)
        
        // Skip transaction summaries - they're in the sidebar
        // But KEEP injury articles - they're important news stories
        if (category === 'transactions') {
          return
        }
        
        const tags = generateTags(article, category)
        
        generatedArticles.push({
          id: `synthesized-${article.id}`,
          title: article.title,
          summary: article.summary || article.title,
          content: article.content || article.summary || '',
          category: category,
          date: article.created_at,
          sourceCount: 2, // Multi-source by definition
          tags: tags,
          imageUrl: article.image_url,
          sourceUrl: article.source_url
        })
      })
      
      // Add daily article
      if (dailyArticle) {
        generatedArticles.push({
          id: 'daily-' + dailyArticle.date,
          title: dailyArticle.title || 'NHL Daily Recap',
          summary: dailyArticle.summary || dailyArticle.content.substring(0, 200) + '...',
          content: dailyArticle.content,
          category: 'all',
          date: dailyArticle.created_at,
          sourceCount: dailyArticle.source_count || 4,
          tags: ['Daily Digest', 'League-Wide', 'AI Generated'],
          imageUrl: dailyArticle.image_url
        })
      }
      
      // Generate Atlantic Division articles (legitimate news content)
      const atlanticGames = games.filter((g: any) => 
        ATLANTIC_TEAMS.includes(g.home_team) || ATLANTIC_TEAMS.includes(g.away_team)
      )
      
      if (atlanticGames.length > 0) {
        const atlanticImage = atlanticGames.find((g: any) => g.image_url)?.image_url || 
                             'https://assets.nhle.com/logos/nhl/svg/MTL_light.svg'
        
        generatedArticles.push({
          id: `atlantic-${Date.now()}`,
          title: `Atlantic Division Update: ${atlanticGames.length} Recent Games`,
          summary: `Latest results from Atlantic Division matchups including ${atlanticGames.slice(0, 2).map((g: any) => `${g.away_team} @ ${g.home_team}`).join(', ')}`,
          content: atlanticGames.map((g: any) => `${g.away_team} @ ${g.home_team}: ${g.away_score}-${g.home_score}`).join('\n'),
          category: 'atlantic',
          date: atlanticGames[0].created_at,
          sourceCount: 3,
          tags: ['Atlantic', 'Division', 'Standings'],
          imageUrl: atlanticImage
        })
      }
      
      setArticles(generatedArticles)
    } catch (error) {
      console.error('Error fetching league articles:', error)
    } finally {
      setLoading(false)
    }
  }

  const determineCategory = (title: string, summary: string): string => {
    const text = `${title} ${summary}`.toLowerCase()
    
    if (text.includes('trade') || text.includes('acquire')) return 'transactions'
    if (text.includes('injur') || text.includes(' ir ') || text.includes('ltir')) return 'injuries'
    if (text.includes('rumor') || text.includes('speculation')) return 'rumors'
    if (text.includes('atlantic') || text.includes('division')) return 'atlantic'
    if (text.includes('sign') || text.includes('contract')) return 'transactions'
    if (text.includes('waiver') || text.includes('recall')) return 'transactions'
    
    return 'all'
  }

  const generateTags = (article: any, category: string): string[] => {
    const tags: string[] = []
    
    // Add category tag
    tags.push(category.toUpperCase())
    
    // Add team tag if present
    if (article.team_code && article.team_code !== 'NHL') {
      tags.push(article.team_code)
    }
    
    // Add multi-source tag
    tags.push('Multi-Source')
    
    return tags
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchArticles()
    setTimeout(() => setRefreshing(false), 500)
  }

  const filteredArticles = articles.filter(article => {
    if (selectedCategory === 'all') return true
    return article.category === selectedCategory
  })

  return (
    <BasePage loadingMessage="LOADING LEAGUE INTELLIGENCE...">
      <div className="min-h-screen bg-gray-950 relative overflow-hidden">
        {/* Animated background grid */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute inset-0" style={{
            backgroundImage: `
              linear-gradient(rgba(6, 182, 212, 0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(6, 182, 212, 0.1) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px'
          }} />
        </div>

        {/* Radial gradient overlay */}
        <div className="absolute inset-0 bg-gradient-radial from-red-600/5 via-transparent to-transparent opacity-30" />

        {/* Content */}
        <div className="relative max-w-screen-2xl mx-auto px-6 pt-8 pb-20">
          {/* Header */}
          {/* Page Header - Simplified */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-12"
          >
            {/* Title - Clean and minimal */}
            <div className="flex items-center space-x-3 mb-6">
              <div className="w-0.5 h-6 bg-gradient-to-b from-white to-transparent" />
              <h1 className="text-2xl font-military-display text-white uppercase tracking-widest">
                League Updates
              </h1>
            </div>

            {/* Category filters */}
            <div className="flex items-center space-x-2 overflow-x-auto pb-2">
              {CATEGORIES.map((category, index) => (
                <motion.button
                  key={category.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  onClick={() => setSelectedCategory(category.id)}
                  className={`
                    flex items-center space-x-1.5 px-4 py-2 rounded border transition-all duration-200 whitespace-nowrap
                    ${selectedCategory === category.id
                      ? 'bg-red-600/10 border-red-600/30 text-red-400'
                      : 'bg-black/20 backdrop-blur-xl border-white/5 text-gray-400 hover:border-white/10 hover:bg-black/30'
                    }
                  `}
                >
                  <span className="text-xs font-military-display uppercase tracking-wider">
                    {category.label}
                  </span>
                  {selectedCategory === category.id && (
                    <span className="text-[10px] font-military-display text-red-600">
                      ({filteredArticles.length})
                    </span>
                  )}
                </motion.button>
              ))}
            </div>
          </motion.div>

          {/* Main Content with Right Sidebar */}
          <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-8">
            
            {/* Left: Articles Grid */}
            <div>
              {loading ? (
                <div className="text-center py-20">
                  <div className="w-8 h-8 border-2 border-red-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                  <div className="text-sm font-military-display text-gray-400">
                    LOADING INTELLIGENCE...
                  </div>
                </div>
              ) : (
                <AnimatePresence mode="wait">
                  <motion.div
                    key={selectedCategory}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
                  >
                    {filteredArticles.map((article, index) => (
                      <motion.div
                        key={article.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.05 }}
                      >
                        <NewsArticleCard
                          title={article.title}
                          summary={article.summary}
                          category={article.category}
                          date={article.date}
                          sourceCount={article.sourceCount}
                          imageUrl={article.imageUrl}
                          tags={article.tags}
                          onClick={() => router.push(`/league/article/${article.id}`)}
                        />
                      </motion.div>
                    ))}
                  </motion.div>
                </AnimatePresence>
              )}

              {/* Empty state */}
              {!loading && filteredArticles.length === 0 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-center py-20"
                >
                  <div className="text-gray-600 font-military-display text-sm mb-2">
                    NO ARTICLES FOUND
                  </div>
                  <div className="text-gray-700 font-military-display text-xs">
                    Try selecting a different category
                  </div>
                </motion.div>
              )}
            </div>

            {/* Right Sidebar: Injuries & Transactions */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 }}
              className="hidden xl:block space-y-6"
            >
              {/* Injuries Tracker */}
              <div className="relative overflow-hidden rounded-lg">
                <div className="absolute inset-0 bg-black/20 backdrop-blur-xl border border-white/5" />
                <div className="relative p-5">
                  <div className="flex items-center space-x-2 mb-4">
                    <div className="w-0.5 h-4 bg-gradient-to-b from-red-400 to-transparent" />
                    <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
                      Injury Reports
                    </h4>
                  </div>
                  <InjuriesTracker limit={8} />
                </div>
              </div>

              {/* Transactions Feed */}
              <div className="relative overflow-hidden rounded-lg">
                <div className="absolute inset-0 bg-black/20 backdrop-blur-xl border border-white/5" />
                <div className="relative p-5">
                  <div className="flex items-center space-x-2 mb-4">
                    <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
                    <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
                      Recent Transactions
                    </h4>
                  </div>
                  <TransactionsQuickFeed limit={12} />
                </div>
              </div>
            </motion.div>

          </div>
        </div>
      </div>
    </BasePage>
  )
}
