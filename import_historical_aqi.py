import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from ...models import HistoricalAQI

def parse_dt(dt_str: str):
    if not dt_str:
        return None
    s = dt_str.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass
    for fmt in (
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None

# ✅ Target cities you will show in UI  ->  Source city names in AQI Bangladesh.csv
PROXY_MAP = {
    "Dhaka": "Dhaka",
    "Chattogram": "Chittagong",
    "Sylhet": "Chhātak",
    "Khulna": "Barisāl",
    "Rajshahi": "Gaibandha",
}

class Command(BaseCommand):
    help = "Import historical AQI using proxy city mapping (fast demo setup)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            default="Authentication/authentication/data/AQI Bangladesh.csv",
            help="Path to the CSV file",
        )
        parser.add_argument(
            "--per_city",
            type=int,
            default=3000,
            help="Rows to import per TARGET city",
        )
        parser.add_argument(
            "--batch",
            type=int,
            default=1000,
            help="Batch size for bulk inserts",
        )

    def handle(self, *args, **options):
        path = options["path"]
        per_city = options["per_city"]
        batch_size = options["batch"]

        # Build reverse lookup: csv city -> target city
        reverse = {src: tgt for tgt, src in PROXY_MAP.items()}

        counts = {tgt: 0 for tgt in PROXY_MAP.keys()}
        buffer = []
        inserted = 0
        skipped = 0

        def to_float(x):
            try:
                return float(x)
            except Exception:
                return None

        def flush():
            nonlocal buffer, inserted
            if not buffer:
                return
            HistoricalAQI.objects.bulk_create(buffer, ignore_conflicts=True)
            inserted += len(buffer)
            buffer = []

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                src_city = (row.get("city_name") or "").strip()

                # only take rows for the proxy source cities
                if src_city not in reverse:
                    skipped += 1
                    continue

                target_city = reverse[src_city]

                if counts[target_city] >= per_city:
                    skipped += 1
                    if all(counts[c] >= per_city for c in counts):
                        break
                    continue

                recorded_at = parse_dt(row.get("datetime") or "")
                if recorded_at is None:
                    skipped += 1
                    continue

                aqi = to_float(row.get("aqi"))
                pm25 = to_float(row.get("pm2_5"))

                buffer.append(HistoricalAQI(
                    city_name=target_city,   # ✅ store TARGET name (Sylhet/Khulna/Rajshahi)
                    recorded_at=recorded_at,
                    aqi=aqi,
                    pm25=pm25,
                    source=f"Proxy source: {src_city} (from AQI Bangladesh.csv)",
                ))
                counts[target_city] += 1

                if len(buffer) >= batch_size:
                    flush()

                if all(counts[c] >= per_city for c in counts):
                    break

            flush()

        self.stdout.write(self.style.SUCCESS(
            f"✅ Imported approx {inserted} rows. Skipped {skipped} rows."
        ))
        self.stdout.write(self.style.SUCCESS(
            "Counts per city: " + ", ".join([f"{c}={counts[c]}" for c in counts])
        ))