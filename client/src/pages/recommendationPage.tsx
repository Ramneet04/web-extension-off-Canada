import { useState } from 'react'
import axios from 'axios'

// ── Types ────────────────────────────────────────────────────────────────────
interface DailyUseSuggestion {
  slot: string
  idea: string
}

interface RecommendedProduct {
  code: string
  product_name: string
  brands: string | null
  proteins_100g: number | null
  fat_100g: number | null
  sugars_100g: number | null
  energy_kcal_100g: number | null
  nutriscore_grade: string | null
  image_url: string | null
}

interface ProductData {
  product_name: string
  brands: string | null
  proteins_100g: number | null
  fat_100g: number | null
  sugars_100g: number | null
  fiber_100g: number | null
  energy_kcal_100g: number | null
  nutriscore_grade: string | null
}

interface RecommendationResult {
  query: string
  intent: 'usage' | 'comparison' | 'general'
  language: string
  product_a: ProductData | null
  product_b: ProductData | null
  advice: string
  comparison_insight: string | null
  daily_use_suggestions: DailyUseSuggestion[]
  recommended_products: RecommendedProduct[]
}

// ── Constants ────────────────────────────────────────────────────────────────
const NUTRI_COLORS: Record<string, string> = {
  a: '#1a7a3a', b: '#5aaa3a', c: '#f5c400', d: '#e07c2a', e: '#c1440e'
}

const SLOT_ICONS: Record<string, string> = {
  breakfast: '🌅',
  smoothie: '🥤',
  'post-workout': '💪',
  snack: '🍎',
  lunch: '🥗',
  dinner: '🍽️',
  default: '✨'
}

function getSlotIcon(slot: string): string {
  return SLOT_ICONS[slot.toLowerCase()] || SLOT_ICONS.default
}

// ── Sub-components ────────────────────────────────────────────────────────────
function LoadingImage({ src, alt, style }: { src: string; alt?: string; style?: React.CSSProperties }) {
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState(false)
  if (error) return <span style={{ fontSize: 32 }}>🥫</span>
  return (
    <>
      {!loaded && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', height: '100%' }}>
          <div style={{
            width: 24, height: 24, border: '3px solid #e8e4dc', borderTop: '3px solid #c1440e',
            borderRadius: '50%', animation: 'spin 0.8s linear infinite'
          }} />
        </div>
      )}
      <img
        src={src} alt={alt || ''}
        style={{ ...style, display: loaded ? 'block' : 'none' }}
        onLoad={() => setLoaded(true)}
        onError={() => setError(true)}
      />
    </>
  )
}

function NutritionBadge({ label, value, unit, highlight }: {
  label: string; value: number | null; unit: string; highlight?: boolean
}) {
  return (
    <div style={{
      background: highlight ? '#e8f4ee' : '#f7f5f0',
      border: highlight ? '1.5px solid #b7dfc8' : '1.5px solid #e8e4dc',
      borderRadius: 10, padding: '8px 12px', textAlign: 'center', minWidth: 70
    }}>
      <div style={{ fontSize: 10, color: '#8a8478', marginBottom: 2 }}>{label}</div>
      <div style={{
        fontSize: 16, fontWeight: 700,
        color: highlight ? '#2d6a4f' : '#1a1814',
        fontFamily: 'Fraunces, serif'
      }}>
        {value != null ? `${Number(value).toFixed(1)}` : '—'}
      </div>
      <div style={{ fontSize: 10, color: '#b0a898' }}>{unit}</div>
    </div>
  )
}

function ProductCard({ product, onClick }: { product: RecommendedProduct; onClick: () => void }) {
  const [hovered, setHovered] = useState(false)
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: 'white',
        border: '1.5px solid #e8e4dc',
        borderRadius: 14,
        padding: 14,
        cursor: 'pointer',
        transition: 'box-shadow 0.2s, transform 0.2s',
        boxShadow: hovered ? '0 6px 20px rgba(0,0,0,0.1)' : '0 1px 4px rgba(0,0,0,0.04)',
        transform: hovered ? 'translateY(-3px)' : 'translateY(0)',
        display: 'flex',
        flexDirection: 'column' as const
      }}
    >
      <div style={{
        height: 80, display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: '#f7f5f0', borderRadius: 8, marginBottom: 10
      }}>
        {product.image_url
          ? <LoadingImage src={product.image_url} style={{ maxHeight: 60, maxWidth: '100%', objectFit: 'contain' }} />
          : <span style={{ fontSize: 28 }}>🥫</span>}
      </div>
      <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 2, lineHeight: 1.3, color: '#1a1814' }}>
        {product.product_name || 'Unknown'}
      </div>
      <div style={{ fontSize: 11, color: '#8a8478', marginBottom: 8 }}>{product.brands}</div>
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 'auto' }}>
        {product.nutriscore_grade && product.nutriscore_grade !== 'unknown' && (
          <span style={{
            background: NUTRI_COLORS[product.nutriscore_grade] || '#aaa',
            color: 'white', fontSize: 9, fontWeight: 700,
            padding: '1px 6px', borderRadius: 4
          }}>
            {product.nutriscore_grade.toUpperCase()}
          </span>
        )}
        {product.proteins_100g != null && (
          <span style={{
            background: '#f0f7f3', color: '#2d6a4f',
            fontSize: 9, padding: '1px 6px', borderRadius: 4
          }}>
            {Number(product.proteins_100g).toFixed(1)}g protein
          </span>
        )}
      </div>
    </div>
  )
}

// ── Comparison Card ───────────────────────────────────────────────────────────
function ComparisonCard({
  productA,
  productB,
  nutrientFocus
}: {
  productA: ProductData
  productB: ProductData
  nutrientFocus?: string
}) {
  const nutrients = [
    { key: 'proteins_100g', label: 'Protein', unit: 'g' },
    { key: 'fat_100g', label: 'Fat', unit: 'g' },
    { key: 'sugars_100g', label: 'Sugars', unit: 'g' },
    { key: 'fiber_100g', label: 'Fiber', unit: 'g' },
    { key: 'energy_kcal_100g', label: 'Calories', unit: 'kcal' },
  ]

  return (
    <div style={{
      background: 'white', border: '1.5px solid #e8e4dc',
      borderRadius: 16, overflow: 'hidden', marginBottom: 24
    }}>
      {/* Header row */}
      <div style={{
        display: 'grid', gridTemplateColumns: '120px 1fr 1fr',
        background: '#f7f5f0', borderBottom: '1.5px solid #e8e4dc'
      }}>
        <div style={{ padding: '14px 16px', fontSize: 11, color: '#8a8478', fontWeight: 600 }}>
          PER 100G
        </div>
        {[productA, productB].map((p, i) => (
          <div key={i} style={{ padding: '14px 16px', borderLeft: '1px solid #e8e4dc' }}>
            <div style={{ fontWeight: 700, fontSize: 13, color: '#1a1814' }}>
              {p.product_name}
            </div>
            {p.brands && (
              <div style={{ fontSize: 11, color: '#8a8478' }}>{p.brands}</div>
            )}
            {p.nutriscore_grade && p.nutriscore_grade !== 'unknown' && (
              <span style={{
                background: NUTRI_COLORS[p.nutriscore_grade] || '#aaa',
                color: 'white', fontSize: 9, fontWeight: 700,
                padding: '1px 6px', borderRadius: 4, marginTop: 4, display: 'inline-block'
              }}>
                {p.nutriscore_grade.toUpperCase()}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Nutrient rows */}
      {nutrients.map((n, i) => {
        const valA = (productA as any)[n.key] as number | null
        const valB = (productB as any)[n.key] as number | null
        const isHighlighted = nutrientFocus && n.label.toLowerCase().includes(nutrientFocus.toLowerCase())
        const higherBetter = ['proteins_100g', 'fiber_100g'].includes(n.key)
        const winnerA = valA != null && valB != null && (higherBetter ? valA > valB : valA < valB)
        const winnerB = valA != null && valB != null && (higherBetter ? valB > valA : valB < valA)

        return (
          <div key={i} style={{
            display: 'grid', gridTemplateColumns: '120px 1fr 1fr',
            borderBottom: i < nutrients.length - 1 ? '1px solid #f0ede8' : 'none',
            background: isHighlighted ? '#fffbf0' : 'white'
          }}>
            <div style={{
              padding: '12px 16px', fontSize: 12, color: '#8a8478', fontWeight: 500,
              display: 'flex', alignItems: 'center', gap: 4
            }}>
              {isHighlighted && <span>⭐</span>}
              {n.label}
            </div>
            {[{ val: valA, winner: winnerA }, { val: valB, winner: winnerB }].map((item, j) => (
              <div key={j} style={{
                padding: '12px 16px', borderLeft: '1px solid #f0ede8',
                display: 'flex', alignItems: 'center', gap: 6
              }}>
                <span style={{
                  fontWeight: item.winner ? 700 : 400,
                  color: item.winner ? '#2d6a4f' : '#1a1814',
                  fontSize: 14
                }}>
                  {item.val != null ? `${Number(item.val).toFixed(n.unit === 'kcal' ? 0 : 1)} ${n.unit}` : '—'}
                </span>
                {item.winner && (
                  <span style={{
                    background: '#e8f4ee', color: '#2d6a4f',
                    fontSize: 9, fontWeight: 700, padding: '1px 5px', borderRadius: 3
                  }}>
                    BETTER
                  </span>
                )}
              </div>
            ))}
          </div>
        )
      })}
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function RecommendationPage({
  result,
  onBack,
  onProductClick,
  sessionId
}: {
  result: RecommendationResult
  onBack: () => void
  onProductClick: (code: string) => void
  sessionId: string
}) {
  const [followUp, setFollowUp] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentResult, setCurrentResult] = useState<RecommendationResult>(result)

  const handleFollowUp = async () => {
    if (!followUp.trim()) return
    setLoading(true)
    try {
      const res = await axios.post('http://localhost:8000/api/recommend', {
        query: followUp,
        product_name: currentResult.product_a?.product_name || null
      }, {
        headers: { 'x-session-id': sessionId }
      })
      setCurrentResult(res.data)
      setFollowUp('')
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  const r = currentResult

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '32px 24px', fontFamily: 'DM Sans, sans-serif' }}>

      {/* Back button */}
      <button onClick={onBack} style={{
        background: 'white', border: '1.5px solid #e8e4dc',
        borderRadius: 10, padding: '8px 16px', fontSize: 13,
        color: '#8a8478', cursor: 'pointer', marginBottom: 24,
        fontFamily: 'DM Sans, sans-serif',
        display: 'flex', alignItems: 'center', gap: 6
      }}>
        ← Back to search
      </button>

      {/* Query header */}
      <div style={{
        background: 'white', border: '1.5px solid #e8e4dc',
        borderRadius: 16, padding: '20px 24px', marginBottom: 24
      }}>
        <div style={{ fontSize: 11, color: '#8a8478', marginBottom: 6, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}>
          {r.intent === 'comparison' ? '⚖️ Comparison' : r.intent === 'usage' ? '💡 Daily Use' : '🥗 Recommendation'}
        </div>
        <div style={{
          fontFamily: 'Fraunces, serif', fontSize: 20,
          fontWeight: 700, color: '#1a1814', marginBottom: 10
        }}>
          "{r.query}"
        </div>
        {/* Advice */}
        <div style={{
          background: '#e8f4ee', border: '1.5px solid #b7dfc8',
          borderRadius: 12, padding: '12px 16px',
          fontSize: 14, color: '#1a1814', lineHeight: 1.6
        }}>
          {r.advice}
        </div>
      </div>

      {/* Comparison table — only shown for comparison intent */}
      {r.intent === 'comparison' && r.product_a && r.product_b && (
        <div style={{ marginBottom: 8 }}>
          <h2 style={{
            fontFamily: 'Fraunces, serif', fontSize: 18,
            fontWeight: 700, color: '#1a1814', marginBottom: 12
          }}>
            Side-by-Side Comparison
          </h2>
          <ComparisonCard
            productA={r.product_a}
            productB={r.product_b}
          />
          {r.comparison_insight && (
            <div style={{
              background: '#fef8f0', border: '1.5px solid #f5deb3',
              borderRadius: 12, padding: '12px 16px',
              fontSize: 14, color: '#1a1814', marginBottom: 24,
              display: 'flex', gap: 10, alignItems: 'flex-start'
            }}>
              <span style={{ fontSize: 20 }}>💡</span>
              <span>{r.comparison_insight}</span>
            </div>
          )}
        </div>
      )}

      {/* Product nutrition snapshot — for usage/general intent */}
      {r.intent !== 'comparison' && r.product_a && (
        <div style={{
          background: 'white', border: '1.5px solid #e8e4dc',
          borderRadius: 16, padding: '20px 24px', marginBottom: 24
        }}>
          <div style={{ fontSize: 11, color: '#8a8478', marginBottom: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}>
            Nutrition Snapshot · {r.product_a.product_name}
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <NutritionBadge label="Protein" value={r.product_a.proteins_100g} unit="g" highlight />
            <NutritionBadge label="Fat" value={r.product_a.fat_100g} unit="g" />
            <NutritionBadge label="Sugars" value={r.product_a.sugars_100g} unit="g" />
            <NutritionBadge label="Fiber" value={r.product_a.fiber_100g} unit="g" />
            <NutritionBadge label="Calories" value={r.product_a.energy_kcal_100g} unit="kcal" />
            {r.product_a.nutriscore_grade && r.product_a.nutriscore_grade !== 'unknown' && (
              <div style={{
                background: NUTRI_COLORS[r.product_a.nutriscore_grade] || '#aaa',
                borderRadius: 10, padding: '8px 12px', textAlign: 'center', minWidth: 70
              }}>
                <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.8)', marginBottom: 2 }}>NUTRI</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: 'white', fontFamily: 'Fraunces, serif' }}>
                  {r.product_a.nutriscore_grade.toUpperCase()}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Daily use suggestions */}
      {r.daily_use_suggestions && r.daily_use_suggestions.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <h2 style={{
            fontFamily: 'Fraunces, serif', fontSize: 18,
            fontWeight: 700, color: '#1a1814', marginBottom: 14
          }}>
            How to Use It Daily
          </h2>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
            gap: 12
          }}>
            {r.daily_use_suggestions.map((s, i) => (
              <div key={i} style={{
                background: 'white', border: '1.5px solid #e8e4dc',
                borderRadius: 14, padding: '16px 18px',
                transition: 'box-shadow 0.2s',
              }}
                onMouseEnter={e => e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.08)'}
                onMouseLeave={e => e.currentTarget.style.boxShadow = 'none'}
              >
                <div style={{ fontSize: 24, marginBottom: 8 }}>
                  {getSlotIcon(s.slot)}
                </div>
                <div style={{
                  fontSize: 11, fontWeight: 700, color: '#2d6a4f',
                  textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 6
                }}>
                  {s.slot}
                </div>
                <div style={{ fontSize: 13, color: '#1a1814', lineHeight: 1.5 }}>
                  {s.idea}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommended products */}
      {r.recommended_products && r.recommended_products.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <h2 style={{
            fontFamily: 'Fraunces, serif', fontSize: 18,
            fontWeight: 700, color: '#1a1814', marginBottom: 6
          }}>
            Products You Might Like
          </h2>
          <p style={{ fontSize: 13, color: '#8a8478', marginBottom: 14, marginTop: 0 }}>
            Based on similar nutritional profile
          </p>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
            gap: 12
          }}>
            {r.recommended_products.map((p, i) => (
              <ProductCard
                key={i}
                product={p}
                onClick={() => onProductClick(p.code)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Follow-up question box */}
      <div style={{
        background: '#f7f5f0', border: '1.5px solid #e8e4dc',
        borderRadius: 16, padding: '18px 20px'
      }}>
        <div style={{ fontSize: 13, color: '#8a8478', marginBottom: 10 }}>
          Ask a follow-up question
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <input
            value={followUp}
            onChange={e => setFollowUp(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleFollowUp()}
            placeholder={
              r.intent === 'comparison'
                ? 'e.g. "Which one is better for weight loss?"'
                : 'e.g. "What about dinner ideas?" or "Is this good for diabetics?"'
            }
            style={{
              flex: 1, border: '1.5px solid #e8e4dc', borderRadius: 10,
              padding: '10px 14px', fontSize: 13,
              fontFamily: 'DM Sans, sans-serif', color: '#1a1814',
              background: 'white', outline: 'none'
            }}
          />
          <button
            onClick={handleFollowUp}
            disabled={loading || !followUp.trim()}
            style={{
              background: '#2d6a4f', color: 'white', border: 'none',
              borderRadius: 10, padding: '10px 20px', fontSize: 13,
              fontFamily: 'DM Sans, sans-serif', fontWeight: 600,
              cursor: loading || !followUp.trim() ? 'not-allowed' : 'pointer',
              opacity: loading || !followUp.trim() ? 0.6 : 1,
              whiteSpace: 'nowrap'
            }}
          >
            {loading ? '…' : 'Ask'}
          </button>
        </div>

        {/* Quick follow-up chips */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 10 }}>
          {(r.intent === 'comparison'
            ? ['Which is better for weight loss?', 'Which has more fiber?', 'Which is more natural?']
            : ['Good for weight loss?', 'Suggest dinner ideas', 'Is it good for diabetics?', 'High protein alternatives?']
          ).map((q, i) => (
            <button key={i} onClick={() => { setFollowUp(q); }}
              style={{
                background: 'white', border: '1px solid #e8e4dc',
                borderRadius: 20, padding: '4px 12px',
                fontSize: 11, color: '#8a8478', cursor: 'pointer',
                fontFamily: 'DM Sans, sans-serif'
              }}>
              {q}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}