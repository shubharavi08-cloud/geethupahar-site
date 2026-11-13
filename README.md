# Personalised song shop — setup

What it is: landing page → 9-step order wizard (audio ₹499 / video ₹999) → Razorpay payment → private admin page where you
see each order, paste the story into Suno, upload the song, click **Render video** (SongReel engine) and **Deliver**
(opens a ready WhatsApp message). Customers get a private link to watch/download. Photos auto-delete 30 days after delivery.

## 1. Before you deploy (edit `config.json`)
`brand` (your site name — currently "Geeth Upahar"), `whatsapp` (91 + 10 digits), `prices`, `deliveryText`, `domain`.
Also read `public/terms.html`, `privacy.html`, `refund.html` once and adjust to your business details (have a lawyer check).

## 2. Try it on any computer (test mode, no payments taken)
`npm install` then `npm start` → open http://localhost:3000 · admin: /admin.html (password `admin123` in test mode).
Without Razorpay keys the site runs in TEST MODE: the Pay button marks the order paid so you can try the whole flow.

## 3. Go live on a VPS (any Ubuntu server with 2+ CPU cores; rendering a 3-min video takes ~10–15 min)
1. Point your domain's A record to the server's IP.
2. Install Docker, copy this folder to the server, `cp .env.example .env` and fill it in.
3. `docker compose up -d --build` — HTTPS is automatic (Caddy). Orders/photos/songs live in `./data` — back it up.

## 4. Razorpay
1. Complete business KYC at razorpay.com, then Settings → API Keys → put Key ID/Secret in `.env`.
2. Settings → Webhooks → URL `https://YOURDOMAIN/api/razorpay/webhook`, events **payment.captured** and **order.paid**,
   set a secret and put it in `RAZORPAY_WEBHOOK_SECRET`. (Test with `rzp_test_` keys first, then switch to live keys.)
3. Razorpay will ask for your Terms, Privacy and Refund pages — they are at /terms.html, /privacy.html, /refund.html.

## 5. Daily use
Admin → click an order → **Copy story for Suno** → make the song → upload mp3 (+ optional `.lrc` timed lyrics for exact
word-by-word captions) → **Render video** → check it plays → **Mark delivered** → send the WhatsApp message.
Sample reels for the landing page: drop `.mp4` files into `public/samples/` (they appear automatically).
