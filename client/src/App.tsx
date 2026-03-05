import { useState } from 'react'
import SearchPage from './pages/SearchPage'
import ProductPage from './pages/ProductPage'

export default function App() {
  const [currentProduct, setCurrentProduct] = useState<string | null>(null)

  return currentProduct
    ? <ProductPage code={currentProduct} onBack={() => setCurrentProduct(null)} />
    : <SearchPage onProductClick={setCurrentProduct} />
}