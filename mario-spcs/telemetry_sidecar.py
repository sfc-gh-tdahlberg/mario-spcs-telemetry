import logging
import time
import json
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.export import PeriodicExportingMetricReader
from opentelemetry.metrics import set_meter_provider, get_meter_provider

SERVICE_NAME = "mario_game"

logger = logging.getLogger(SERVICE_NAME)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("%(asctime)s;%(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S"))
logger.addHandler(ch)

tracer_provider = TracerProvider(
    resource=Resource.create({"service.name": SERVICE_NAME})
)
span_processor = BatchSpanProcessor(
    span_exporter=OTLPSpanExporter(insecure=True),
    schedule_delay_millis=5000
)
tracer_provider.add_span_processor(span_processor)
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(SERVICE_NAME)

metric_exporter = OTLPMetricExporter(insecure=True)
metric_reader = PeriodicExportingMetricReader(exporter=metric_exporter, export_interval_millis=5000)
meter_provider = MeterProvider(metric_readers=[metric_reader], resource=Resource.create({"service.name": SERVICE_NAME}))
set_meter_provider(meter_provider)
meter = get_meter_provider().get_meter(SERVICE_NAME)

game_start_counter = meter.create_counter(name="mario.game.start", description="Number of game starts")
game_death_counter = meter.create_counter(name="mario.game.death", description="Number of Mario deaths")
level_win_counter = meter.create_counter(name="mario.level.win", description="Number of level wins")
game_win_counter = meter.create_counter(name="mario.game.win", description="Number of full game wins")
game_over_counter = meter.create_counter(name="mario.game.over", description="Number of game overs")
key_press_counter = meter.create_counter(name="mario.key.press", description="Key press events")
level_start_counter = meter.create_counter(name="mario.level.start", description="Level starts")
coin_counter = meter.create_counter(name="mario.coin.collect", description="Coins collected")
powerup_counter = meter.create_counter(name="mario.powerup.spawn", description="Powerups spawned")
session_duration_histogram = meter.create_histogram(name="mario.session.duration", description="Session duration in seconds", unit="s")


class TelemetryHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.startswith("/telemetry"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
                data["player_name"] = self._get_player_name()
                self._process_event(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                origin = self.headers.get("Origin", "*")
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Credentials", "true")
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
            except Exception as e:
                logger.error(f"Error processing telemetry: {e}")
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        origin = self.headers.get("Origin", "*")
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        logger.info(f"HTTP {args[0] if args else ''}")

    PIXEL_GIF = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

    def _get_player_name(self):
        user = self.headers.get("Sf-Context-Current-User", "").strip()
        if not user:
            user = self.headers.get("sf-context-current-user", "").strip()
        result = user or None
        logger.info(f"PLAYER_NAME from header: {result!r}")
        return result

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/whoami":
            player = self._get_player_name() or "unknown"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store, no-cache")
            self.end_headers()
            self.wfile.write(json.dumps({"player_name": player}).encode())
        elif parsed.path.startswith("/telemetry"):
            header_player = self._get_player_name()
            params = parse_qs(parsed.query)
            d = params.get("d", [None])[0]
            if d:
                try:
                    data = json.loads(unquote(d))
                    browser_player = data.get("player_name", "") or ""
                    data["player_name"] = header_player or browser_player or "unknown"
                    logger.info(f"EVENT {data.get('event')} player_name={data['player_name']!r} (header={header_player!r}, browser={browser_player!r})")
                    self._process_event(data)
                except Exception as e:
                    logger.error(f"Error processing GET telemetry: {e}")
            self.send_response(200)
            self.send_header("Content-Type", "image/gif")
            self.send_header("Cache-Control", "no-store, no-cache")
            self.send_header("Content-Length", str(len(self.PIXEL_GIF)))
            self.end_headers()
            self.wfile.write(self.PIXEL_GIF)
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"telemetry_sidecar_alive"}')

    def _process_event(self, data):
        event_type = data.get("event", "unknown")
        attrs = {k: str(v) for k, v in data.items() if k != "event"}

        with tracer.start_as_current_span(f"mario.{event_type}") as span:
            for k, v in attrs.items():
                span.set_attribute(k, v)

            if event_type == "game_start":
                game_start_counter.add(1)
                logger.info(f"GAME_START lives={attrs.get('lives')}")

            elif event_type == "death":
                game_death_counter.add(1, {"level": attrs.get("level", "?")})
                logger.info(f"DEATH level={attrs.get('level')} lives={attrs.get('lives')} large={attrs.get('large')} fire={attrs.get('fire')}")

            elif event_type == "level_win":
                level_win_counter.add(1, {"level": attrs.get("level", "?")})
                logger.info(f"LEVEL_WIN level={attrs.get('level')} time_left={attrs.get('time_left')}")

            elif event_type == "game_win":
                game_win_counter.add(1)
                logger.info(f"GAME_WIN duration={attrs.get('session_duration')}s")

            elif event_type == "game_over":
                game_over_counter.add(1)
                logger.info(f"GAME_OVER level={attrs.get('level')} coins={attrs.get('coins')} duration={attrs.get('session_duration')}s")

            elif event_type == "game_over_screen":
                logger.info(f"GAME_OVER_SCREEN duration={attrs.get('session_duration')}s")

            elif event_type == "level_start":
                level_start_counter.add(1, {"level": attrs.get("level", "?"), "difficulty": attrs.get("difficulty", "?")})
                logger.info(f"LEVEL_START level={attrs.get('level')} difficulty={attrs.get('difficulty')} type={attrs.get('type')}")

            elif event_type == "key_press":
                key_press_counter.add(1, {"key": attrs.get("key", "?")})

            elif event_type == "coin":
                coin_counter.add(1)
                logger.info(f"COIN total={attrs.get('total_coins')}")

            elif event_type == "powerup_spawn":
                powerup_counter.add(1, {"type": attrs.get("type", "?")})
                logger.info(f"POWERUP type={attrs.get('type')} level={attrs.get('level')}")

            elif event_type == "session_end":
                duration = float(attrs.get("duration", attrs.get("session_duration", 0)))
                session_duration_histogram.record(duration)
                logger.info(f"SESSION_END duration={duration}s")

            elif event_type == "telemetry_init":
                logger.info("TELEMETRY_INIT client connected")

            elif event_type == "title_screen":
                logger.info("TITLE_SCREEN displayed")

            else:
                logger.info(f"UNKNOWN_EVENT type={event_type} attrs={attrs}")


if __name__ == "__main__":
    logger.info("Telemetry sidecar starting on port 9090")
    server = HTTPServer(("0.0.0.0", 9090), TelemetryHandler)
    server.serve_forever()
