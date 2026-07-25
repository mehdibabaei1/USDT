name: Tether Price Update

on:
  schedule:
    # هر 15 دقیقه اجرا می‌شود (GitHub ممکن است برای ریپازیتوری‌های کم‌فعالیت این را کمتر کند)
    - cron: "*/15 * * * *"
  workflow_dispatch: {}   # امکان اجرای دستی از تب Actions برای تست

jobs:
  send-price:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Debug AbanTether response
        env:
          ABANTETHER_API_KEY: ${{ secrets.ABANTETHER_API_KEY }}
        run: |
          curl -v -L "https://abantether.com/api/v1/otc/coin-price/?coin=USDT" \
            -H "Authorization: Bearer $ABANTETHER_API_KEY" \
            -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)" \
            || true

      - name: Run bot
        env:
          BOT_TOKEN: ${{ secrets.BOT_TOKEN }}
          CHANNEL_ID: ${{ secrets.CHANNEL_ID }}
          ABANTETHER_API_KEY: ${{ secrets.ABANTETHER_API_KEY }}
        run: python tether_price_bot.py
