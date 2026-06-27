from __future__ import annotations

import os

from jiomart_price_tracker.web import create_app

app = create_app()


def main() -> None:
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)


if __name__ == "__main__":
    main()
