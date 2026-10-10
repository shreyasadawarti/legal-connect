const CHECKOUT_SRC = 'https://checkout.razorpay.com/v1/checkout.js'
let loader: Promise<void> | null = null

export interface RazorpayHandlerResponse {
  razorpay_payment_id: string
  razorpay_order_id: string
  razorpay_signature: string
}

export interface RazorpayOptions {
  key: string
  amount: number
  currency: string
  order_id: string
  name: string
  description?: string
}

interface RazorpayInstance {
  open: () => void
  on: (event: string, handler: (payload: unknown) => void) => void
}

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => RazorpayInstance
  }
}

function loadCheckout(): Promise<void> {
  if (window.Razorpay) return Promise.resolve()
  if (loader) return loader
  loader = new Promise<void>((resolve, reject) => {
    const script = document.createElement('script')
    script.src = CHECKOUT_SRC
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => {
      loader = null
      reject(new Error('Could not load the payment checkout. Check your connection.'))
    }
    document.body.appendChild(script)
  })
  return loader
}

export function openRazorpayCheckout(
  options: RazorpayOptions,
): Promise<RazorpayHandlerResponse> {
  return loadCheckout().then(
    () =>
      new Promise<RazorpayHandlerResponse>((resolve, reject) => {
        if (!window.Razorpay) {
          reject(new Error('Payment checkout is unavailable.'))
          return
        }
        const instance = new window.Razorpay({
          ...options,
          theme: { color: '#2563eb' },
          handler: (response: RazorpayHandlerResponse) => resolve(response),
          modal: {
            ondismiss: () => reject(new Error('PAYMENT_CANCELLED')),
          },
        })
        instance.on('payment.failed', () => reject(new Error('PAYMENT_FAILED')))
        instance.open()
      }),
  )
}
