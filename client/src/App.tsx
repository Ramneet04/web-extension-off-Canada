import { useState } from 'react'
import SearchPage from './pages/SearchPage'
import ProductPage from './pages/ProductPage'

export default function App() {
  const [currentProduct, setCurrentProduct] = useState<string | null>(null)

  return (
    <>
      <div style={{ display: currentProduct ? 'none' : 'block' }}>
        <SearchPage onProductClick={setCurrentProduct} />
      </div>
      {currentProduct && (
        <ProductPage code={currentProduct} onBack={() => setCurrentProduct(null)} onProductClick={setCurrentProduct} />
      )}
    </>
  )
}