import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY as string, { apiVersion: "2024-06-20" });

const prices: Record<string, string> = {
  basic: process.env.STRIPE_PRICE_BASIC as string,
  pro: process.env.STRIPE_PRICE_PRO as string,
  premium: process.env.STRIPE_PRICE_PREMIUM as string,
};

export async function POST(req: NextRequest) {
  try {
    const { planId } = (await req.json()) as { planId: string };
    if (!prices[planId]) return NextResponse.json({ error: "Unknown plan" }, { status: 400 });

    const successUrl = process.env.CHECKOUT_SUCCESS_URL!;
    const cancelUrl = process.env.CHECKOUT_CANCEL_URL!;
    const setupPrice = process.env.STRIPE_PRICE_SETUP!;

    const session = await stripe.checkout.sessions.create({
      mode: "subscription",
      line_items: [
        { price: setupPrice, quantity: 1 },
        { price: prices[planId], quantity: 1 },
      ],
      success_url: successUrl,
      cancel_url: cancelUrl,
      allow_promotion_codes: true,
      metadata: { planId },
    });

    return NextResponse.json({ url: session.url });
  } catch (e: any) {
    console.error(e);
    return NextResponse.json({ error: e.message || "Stripe error" }, { status: 500 });
  }
}
