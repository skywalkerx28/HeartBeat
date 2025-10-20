'use client'

export interface InfoField {
  label: string
  value: string | number
}

interface ProfileInfoCardProps {
  title: string
  subtitle?: string
  description?: string
  fields: InfoField[]
  imageUrl?: string
}

export function ProfileInfoCard({
  title,
  subtitle,
  description,
  fields,
  imageUrl,
}: ProfileInfoCardProps) {
  return (
    <div className="relative overflow-hidden rounded-lg">
      {/* Background with blur effect - matching the page style */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
      
      {/* Content */}
      <div className="relative p-4">
        {/* Header */}
        <div className="flex items-center space-x-3 mb-4">
          {imageUrl && (
            <div className="w-10 h-10 rounded-lg bg-black/40 border border-white/10 flex items-center justify-center overflow-hidden flex-shrink-0">
              <img
                src={imageUrl}
                alt={title}
                className="w-full h-full object-contain"
              />
            </div>
          )}
          <div className="flex-1 min-w-0">
            <h2 className="text-base font-military-display text-white uppercase tracking-wider truncate">
              {title}
            </h2>
            {subtitle && (
              <div className="text-xs font-military-display text-gray-400 truncate">
                {subtitle}
              </div>
            )}
          </div>
        </div>

        {/* Fields */}
        <div className="space-y-2 mb-4">
          {fields.map((field, idx) => (
            <div
              key={idx}
              className="grid grid-cols-12 gap-3 py-1.5 border-b border-white/5 last:border-0"
            >
              <span className="col-span-5 text-xs font-military-display text-gray-500 uppercase tracking-wider">
                {field.label}
              </span>
              <span className="col-span-7 text-sm font-military-display text-white text-right break-words whitespace-normal leading-snug">
                {field.value}
              </span>
            </div>
          ))}
        </div>

        {/* Description Section */}
        {description && (
          <div className="pt-4 border-t border-white/5">
            <div className="text-xs font-military-display text-gray-500 leading-relaxed">
              {description}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
