import { useState } from 'react'
import SearchPage from './pages/SearchPage'
import ProductPage from './pages/ProductPage'

type View =
  | { type: 'search' }
  | { type: 'product'; code: string }

export default function App() {
  const [view, setView] = useState<View>({ type: 'search' })

  const goToProduct = (code: string) => setView({ type: 'product', code })
  const goBack = () => setView({ type: 'search' })

  if (view.type === 'product') {
    return (
      <ProductPage
        code={view.code}
        onBack={goBack}
        onProductClick={goToProduct}
      />
    )
  }

  return (
    <SearchPage onProductClick={goToProduct} />
  )
}