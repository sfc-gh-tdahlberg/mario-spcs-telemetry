var MarioTelemetry = (function() {
    var SIDECAR_URL = window.location.protocol + "//" + window.location.host + "/telemetry";
    var WHOAMI_URL = window.location.protocol + "//" + window.location.host + "/whoami";
    var sessionStart = Date.now();
    var playerName = "unknown";
    var eventQueue = [];
    var flushInterval = null;

    function send(data) {
        eventQueue.push(data);
    }

    function flush() {
        if (eventQueue.length === 0) return;
        var batch = eventQueue.splice(0, eventQueue.length);
        for (var i = 0; i < batch.length; i++) {
            try {
                var encoded = encodeURIComponent(JSON.stringify(batch[i]));
                var img = new Image();
                img.src = SIDECAR_URL + "?d=" + encoded + "&_t=" + Date.now();
            } catch(e) {
                console.warn("Telemetry pixel error: " + e);
            }
        }
    }

    function fetchPlayerName() {
        try {
            var xhr = new XMLHttpRequest();
            xhr.open("GET", WHOAMI_URL, true);
            xhr.onload = function() {
                if (xhr.status === 200) {
                    try {
                        var resp = JSON.parse(xhr.responseText);
                        if (resp.player_name && resp.player_name !== "unknown") {
                            playerName = resp.player_name;
                            showPlayerBanner(playerName);
                            console.log("Player identified: " + playerName);
                        }
                    } catch(e) { console.warn("whoami parse error: " + e); }
                }
            };
            xhr.send();
        } catch(e) { console.warn("whoami fetch error: " + e); }
    }

    function showPlayerBanner(name) {
        var existing = document.getElementById("mario-player-banner");
        if (existing) existing.remove();
        var banner = document.createElement("div");
        banner.id = "mario-player-banner";
        banner.style.cssText = "position:fixed;top:8px;right:8px;z-index:99999;background:rgba(0,0,0,0.75);color:#FFD700;font-family:'Press Start 2P',monospace;font-size:11px;padding:6px 12px;border-radius:4px;border:2px solid #FFD700;pointer-events:none;text-shadow:1px 1px 0 #000;";
        banner.textContent = "\u2605 " + name;
        document.body.appendChild(banner);
    }

    function init() {
        fetchPlayerName();
        flushInterval = setInterval(flush, 2000);

        var origTitleEnter = Mario.TitleState.prototype.Enter;
        Mario.TitleState.prototype.Enter = function() {
            origTitleEnter.call(this);
            send({event: "title_screen", timestamp: Date.now()});
        };

        var origTitleCheck = Mario.TitleState.prototype.CheckForChange;
        Mario.TitleState.prototype.CheckForChange = function(context) {
            var wasPressing = Enjine.KeyboardInput.IsKeyDown(Enjine.Keys.S);
            origTitleCheck.call(this, context);
            if (wasPressing) {
                send({event: "game_start", timestamp: Date.now(), lives: Mario.MarioCharacter.Lives, player_name: playerName});
            }
        };

        var origLevelEnter = Mario.LevelState.prototype.Enter;
        Mario.LevelState.prototype.Enter = function() {
            origLevelEnter.call(this);
            send({
                event: "level_start",
                timestamp: Date.now(),
                level: Mario.MarioCharacter.LevelString,
                difficulty: this.LevelDifficulty,
                type: this.LevelType,
                lives: Mario.MarioCharacter.Lives,
                coins: Mario.MarioCharacter.Coins,
                player_name: playerName
            });
        };

        var origLevelCheck = Mario.LevelState.prototype.CheckForChange;
        Mario.LevelState.prototype.CheckForChange = function(context) {
            if (this.GotoLoseState && !this._telemetryLoseSent) {
                this._telemetryLoseSent = true;
                send({
                    event: "game_over",
                    timestamp: Date.now(),
                    level: Mario.MarioCharacter.LevelString,
                    coins: Mario.MarioCharacter.Coins,
                    session_duration: (Date.now() - sessionStart) / 1000,
                    player_name: playerName
                });
            }
            if (Mario.MarioCharacter.DeathTime > 0 && !this._telemetryDeathSent) {
                this._telemetryDeathSent = true;
                send({
                    event: "death",
                    timestamp: Date.now(),
                    level: Mario.MarioCharacter.LevelString,
                    lives: Mario.MarioCharacter.Lives,
                    coins: Mario.MarioCharacter.Coins,
                    large: Mario.MarioCharacter.Large,
                    fire: Mario.MarioCharacter.Fire,
                    player_name: playerName
                });
            }
            if (Mario.MarioCharacter.WinTime > 0 && !this._telemetryWinSent) {
                this._telemetryWinSent = true;
                send({
                    event: "level_win",
                    timestamp: Date.now(),
                    level: Mario.MarioCharacter.LevelString,
                    lives: Mario.MarioCharacter.Lives,
                    coins: Mario.MarioCharacter.Coins,
                    time_left: this.TimeLeft | 0,
                    player_name: playerName
                });
            }
            origLevelCheck.call(this, context);
        };

        var origGetCoin = Mario.Character.prototype.GetCoin;
        if (origGetCoin) {
            Mario.Character.prototype.GetCoin = function() {
                origGetCoin.call(this);
                send({event: "coin", timestamp: Date.now(), total_coins: this.Coins, player_name: playerName});
            };
        }

        var origBump = Mario.LevelState.prototype.Bump;
        Mario.LevelState.prototype.Bump = function(x, y, canBreakBricks) {
            var block = this.Level.GetBlock(x, y);
            if ((Mario.Tile.Behaviors[block & 0xff] & Mario.Tile.Special) > 0) {
                if (!Mario.MarioCharacter.Large) {
                    send({event: "powerup_spawn", timestamp: Date.now(), type: "mushroom", level: Mario.MarioCharacter.LevelString, player_name: playerName});
                } else {
                    send({event: "powerup_spawn", timestamp: Date.now(), type: "fire_flower", level: Mario.MarioCharacter.LevelString, player_name: playerName});
                }
            }
            origBump.call(this, x, y, canBreakBricks);
        };

        var origWinEnter = Mario.WinState.prototype.Enter;
        Mario.WinState.prototype.Enter = function() {
            origWinEnter.call(this);
            send({
                event: "game_win",
                timestamp: Date.now(),
                session_duration: (Date.now() - sessionStart) / 1000
            });
        };

        var origLoseEnter = Mario.LoseState.prototype.Enter;
        Mario.LoseState.prototype.Enter = function() {
            origLoseEnter.call(this);
            send({
                event: "game_over_screen",
                timestamp: Date.now(),
                session_duration: (Date.now() - sessionStart) / 1000
            });
        };

        var keyNames = {37: "left", 38: "up", 39: "right", 40: "down", 65: "A_sprint", 83: "S_jump"};
        var keyThrottle = {};
        document.addEventListener("keydown", function(e) {
            var name = keyNames[e.keyCode];
            if (name) {
                var now = Date.now();
                if (!keyThrottle[name] || now - keyThrottle[name] > 500) {
                    keyThrottle[name] = now;
                    send({event: "key_press", key: name, timestamp: now, player_name: playerName});
                }
            }
        });

        window.addEventListener("beforeunload", function() {
            send({event: "session_end", timestamp: Date.now(), session_duration: (Date.now() - sessionStart) / 1000, player_name: playerName});
            flush();
        });

        send({event: "telemetry_init", timestamp: Date.now()});
        console.log("Mario Telemetry initialized - player: " + playerName);
    }

    return {init: init};
})();

$(document).ready(function() {
    var checkReady = setInterval(function() {
        if (typeof Mario !== "undefined" && typeof Mario.TitleState !== "undefined") {
            clearInterval(checkReady);
            MarioTelemetry.init();
        }
    }, 100);
});
