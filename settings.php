<?php
// Loaded inside FPP's authenticated plugin wrapper.
$loeConfigPath = __DIR__ . '/.private/config.json';
$loeConfig = is_file($loeConfigPath) ? json_decode(file_get_contents($loeConfigPath), true) : [];
if (!is_array($loeConfig)) $loeConfig = [];
$loeCsrf = trim((string)@file_get_contents(__DIR__ . '/.private/csrf.key'));
if (!preg_match('/^[a-f0-9]{64}$/D', $loeCsrf)) {
    echo '<div class="alert alert-danger">Plugin installation is incomplete. Run its install script before changing settings.</div>';
    return;
}
$loeMessage = '';
$loeError = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    try {
        if (!hash_equals($loeCsrf, (string)($_POST['loe_csrf'] ?? ''))) throw new RuntimeException('Please reload this page and try again.');
        $endpoint = trim((string)($_POST['loe_endpoint'] ?? ''));
        $url = parse_url($endpoint);
        if (!$url || ($url['scheme'] ?? '') !== 'https' || empty($url['host']) || ($url['path'] ?? '') !== '/api/lyrics/status' || isset($url['user']) || isset($url['pass']) || isset($url['query']) || isset($url['fragment'])) throw new RuntimeException('Use an HTTPS website address ending in /api/lyrics/status.');
        $token = trim((string)($_POST['loe_token'] ?? ''));
        if ($token === '') $token = $loeConfig['token'] ?? '';
        if (!preg_match('/^[a-f0-9]{64}$/D', $token)) throw new RuntimeException('Enter the separate 64-character website lyrics key.');
        $interval = filter_var($_POST['loe_interval'] ?? '', FILTER_VALIDATE_INT);
        if ($interval === false || $interval < 1 || $interval > 5) throw new RuntimeException('The update interval must be between 1 and 5 seconds.');
        $next = array_replace($loeConfig, ['endpoint' => $endpoint, 'token' => $token, 'enabled' => isset($_POST['loe_enabled']), 'interval_seconds' => $interval, 'fpp_url' => 'http://127.0.0.1']);
        $temp = tempnam(__DIR__ . '/.private', 'config-');
        if ($temp === false) throw new RuntimeException('Cannot create the private configuration file.');
        try {
            chmod($temp, 0600);
            if (file_put_contents($temp, json_encode($next, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR) . "\n", LOCK_EX) === false || !rename($temp, $loeConfigPath)) throw new RuntimeException('Cannot save the private configuration file.');
        } finally {
            if (is_file($temp)) unlink($temp);
        }
        $loeConfig = $next;
        $loeMessage = 'Saved. The lyrics sender will apply these settings within a few seconds.';
    } catch (Throwable $e) {
        $loeError = $e instanceof RuntimeException ? $e->getMessage() : 'Unable to save settings.';
    }
}
$loeEscape = static fn($value) => htmlspecialchars((string)$value, ENT_QUOTES, 'UTF-8');
?>
<div class="container-fluid">
  <h2>Live Website Lyrics</h2>
  <p>Shares the current song and playback position with your sing-along website. Aircraft lighting blackouts leave the music and lyrics running.</p>
  <?php if ($loeMessage): ?><div class="alert alert-success"><?= $loeEscape($loeMessage) ?></div><?php endif ?>
  <?php if ($loeError): ?><div class="alert alert-danger"><?= $loeEscape($loeError) ?></div><?php endif ?>
  <form method="post" autocomplete="off">
    <input type="hidden" name="loe_csrf" value="<?= $loeEscape($loeCsrf) ?>">
    <div class="form-group mb-3"><label><input type="checkbox" name="loe_enabled" value="1" <?= !empty($loeConfig['enabled']) ? 'checked' : '' ?>> Send live lyrics updates</label></div>
    <div class="form-group mb-3"><label for="loe_endpoint">Website receiver</label><input class="form-control" type="url" id="loe_endpoint" name="loe_endpoint" required value="<?= $loeEscape($loeConfig['endpoint'] ?? 'https://lightsonelizabeth.com/api/lyrics/status') ?>"></div>
    <div class="form-group mb-3"><label for="loe_token">Website lyrics key</label><input class="form-control" type="password" id="loe_token" name="loe_token" autocomplete="new-password" placeholder="Leave blank to keep the saved key"><small>The saved key is never displayed. Use the lyrics receiver key, not your FPP or website login password.</small></div>
    <div class="form-group mb-3"><label for="loe_interval">Update interval (seconds)</label><input class="form-control" type="number" min="1" max="5" id="loe_interval" name="loe_interval" value="<?= $loeEscape($loeConfig['interval_seconds'] ?? 2) ?>" required></div>
    <p><?= count($loeConfig['sequence_media'] ?? []) ?> sequence-to-song mappings configured. Saving these settings preserves them.</p>
    <button type="submit" class="btn btn-primary">Save settings</button>
  </form>
  <hr>
  <p>Logs: <code>plugin-fpp-plugin-loe-lyrics.log</code> in FPP's log viewer. Disabling updates stops website synchronisation; playback continues normally.</p>
  <p>This plugin reads FPP's status API. It does not alter FPP core, playlists, sequences or aircraft blackout controls.</p>
</div>
