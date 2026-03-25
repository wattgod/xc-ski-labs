<?php
/**
 * XC Ski Labs — GA4 Analytics
 *
 * Injects Google Analytics 4 tracking snippet into <head>.
 * Skips for logged-in admins/editors.
 *
 * Measurement ID: G-3JQLSQLPPM (XC Ski Labs property)
 */

defined('ABSPATH') || exit;

add_action('wp_head', function () {
    // Skip tracking for admins and editors
    if (is_user_logged_in() && current_user_can('edit_posts')) {
        return;
    }

    $ga4_id = 'G-3JQLSQLPPM';
    ?>
<!-- XC Ski Labs GA4 -->
<script async src="https://www.googletagmanager.com/gtag/js?id=<?php echo esc_attr($ga4_id); ?>"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', '<?php echo esc_js($ga4_id); ?>');
</script>
<!-- /XC Ski Labs GA4 -->
    <?php
}, 1);
