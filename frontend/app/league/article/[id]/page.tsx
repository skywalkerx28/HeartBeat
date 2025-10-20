'use client'

import React, { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { ArrowLeftIcon, ClockIcon, SparklesIcon, LinkIcon } from '@heroicons/react/24/outline'
import { BasePage } from '../../../../components/layout/BasePage'

interface Article {
  id: number
  title: string
  content: string
  summary?: string
  team_code: string
  date: string
  image_url?: string
  source_url?: string
  metadata?: {
    sources?: string[]
    source_count?: number
    source_urls?: string[]
    is_multi_source?: boolean
  }
  created_at: string
}

export default function ArticleReaderPage() {
  const router = useRouter()
  const params = useParams()
  const articleId = params?.id as string
  
  const [article, setArticle] = useState<Article | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchArticle()
  }, [articleId])

  const fetchArticle = async () => {
    try {
      // Extract the actual DB ID from the article ID (format: synthesized-123)
      const dbId = articleId?.replace('synthesized-', '').replace('daily-', '')
      
      // Fetch all articles and find the matching one
      const response = await fetch('/api/v1/news/synthesized-articles?days=30')
      const data = await response.json()
      
      const foundArticle = data.find((a: any) => 
        articleId?.includes(String(a.id)) || articleId?.includes(a.date)
      )
      
      setArticle(foundArticle || null)
    } catch (error) {
      console.error('Error fetching article:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', { 
      month: 'long', 
      day: 'numeric', 
      year: 'numeric' 
    })
  }

  if (loading) {
    return (
      <BasePage>
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

          <div className="relative max-w-4xl mx-auto px-6 py-20 text-center">
            <div className="w-8 h-8 border-2 border-red-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <div className="text-sm font-military-display text-gray-400">
              LOADING ARTICLE...
            </div>
          </div>
        </div>
      </BasePage>
    )
  }

  if (!article) {
    return (
      <BasePage>
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

          <div className="relative max-w-4xl mx-auto px-6 py-20 text-center">
            <div className="text-2xl font-military-display text-white mb-4">
              ARTICLE NOT FOUND
            </div>
            <button
              onClick={() => router.push('/league')}
              className="text-sm font-military-display text-red-400 hover:text-red-300 transition-colors"
            >
              ← RETURN TO LEAGUE UPDATES
            </button>
          </div>
        </div>
      </BasePage>
    )
  }

  return (
    <BasePage>
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

        {/* Article Content */}
        <div className="relative max-w-4xl mx-auto px-6 pt-8 pb-20">
          {/* Back Button */}
          <motion.button
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            onClick={() => router.push('/league')}
            className="flex items-center space-x-2 text-sm font-military-display text-gray-400 hover:text-white transition-colors mb-8 group"
          >
            <ArrowLeftIcon className="w-4 h-4" />
            <span>BACK TO LEAGUE UPDATES</span>
          </motion.button>

          {/* Featured Image */}
          {article.image_url && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="relative mb-8 rounded-lg overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-t from-gray-950 via-transparent to-transparent z-10" />
              <img
                src={article.image_url}
                alt={article.title}
                className="w-full h-[400px] object-cover"
              />
            </motion.div>
          )}

          {/* Article Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mb-8"
          >
            {/* Title */}
            <h1 className="text-4xl font-military-display text-white tracking-wider mb-6 leading-tight">
              {article.title}
            </h1>

            {/* Metadata */}
            <div className="flex items-center space-x-6 text-sm font-military-display text-gray-400">
              <div className="flex items-center space-x-2">
                <ClockIcon className="w-4 h-4" />
                <span>{formatDate(article.created_at)}</span>
              </div>

              <div className="flex items-center space-x-2">
                <SparklesIcon className="w-4 h-4 text-red-400" />
                <span className="text-red-400">AI SYNTHESIZED</span>
              </div>

              {article.source_url && (
                <a
                  href={article.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center space-x-2 hover:text-white transition-colors"
                >
                  <LinkIcon className="w-4 h-4" />
                  <span>VIEW SOURCE</span>
                </a>
              )}

              <div className="px-2 py-1 bg-red-600/10 border border-red-600/20 rounded text-red-400 text-xs">
                {article.team_code}
              </div>
            </div>
          </motion.div>

          {/* Article Content */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="prose prose-invert max-w-none"
          >
            {/* Glass container for content */}
            <div className="relative rounded-lg overflow-hidden">
              <div className="absolute inset-0 bg-black/20 backdrop-blur-xl border border-white/5" />
              
              <div className="relative p-8">
                {/* Article body with proper formatting */}
                <div className="text-base font-sans text-gray-300 leading-relaxed space-y-6">
                  {article.content.split('\n\n').map((paragraph, index) => (
                    <p key={index} className="text-gray-300">
                      {paragraph}
                    </p>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>

          {/* Footer - Source Citation */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="mt-12 pt-8 border-t border-white/5"
          >
            <div className="flex items-center justify-between">
              {article.metadata?.sources && article.metadata.sources.length > 0 ? (
                <div className="flex items-center space-x-2 text-xs font-military-display text-gray-600">
                  <span className="uppercase tracking-wider">
                    {article.metadata.is_multi_source ? 'Synthesized from' : 'Source'}:
                  </span>
                  {article.metadata.sources.map((source, index) => {
                    // Map source codes to display names and URLs
                    const sourceMap: Record<string, { name: string; url: string }> = {
                      'nhl': { name: 'NHL.com', url: 'https://www.nhl.com' },
                      'sportsnet': { name: 'Sportsnet', url: 'https://www.sportsnet.ca' },
                      'dailyfaceoff': { name: 'DailyFaceoff', url: 'https://www.dailyfaceoff.com' },
                      'capwages': { name: 'CapWages', url: 'https://capwages.com' },
                      'tsn': { name: 'TSN', url: 'https://www.tsn.ca' }
                    }
                    
                    const sourceInfo = sourceMap[source] || { name: source.toUpperCase(), url: article.source_url || '#' }
                    
                    return (
                      <React.Fragment key={source}>
                        {index > 0 && <span>•</span>}
                        <a 
                          href={sourceInfo.url}
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="hover:text-gray-400 transition-colors"
                        >
                          {sourceInfo.name}
                        </a>
                      </React.Fragment>
                    )
                  })}
                </div>
              ) : (
                <div className="text-xs font-military-display text-gray-600">
                  <span className="uppercase tracking-wider">Source: </span>
                  <a 
                    href={article.source_url || 'https://www.nhl.com'} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="hover:text-gray-400 transition-colors"
                  >
                    NHL.com
                  </a>
                </div>
              )}

              <button
                onClick={() => router.push('/league')}
                className="px-4 py-2 text-xs font-military-display text-white border border-white/10 rounded hover:bg-white/5 hover:border-white/20 transition-all"
              >
                BACK TO LEAGUE
              </button>
            </div>
          </motion.div>
        </div>
      </div>
    </BasePage>
  )
}

