"""Internationalization (i18n) messages for the sync sitemap tool.

Supports English (en) and French (fr) translations for all user-facing messages.
"""

from typing import Any

# Message dictionary with all supported translations
MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "starting_sync": "🚀 Starting sitemap sync from:\n{url}\n",
        "starting_sync_manual": "🚀 Starting sync from manual URL list ({count} URLs)\n",
        "starting_sync_both": "🚀 Starting sync from sitemap + manual URLs ({count} URLs total)\n",
        "dry_run_mode": "🔍 DRY RUN MODE: No changes will be made\n",
        "no_urls_found": "❌ No URLs found in sitemap\n",
        "found_urls": "📋 Found {count} URLs in sitemap\n",
        "after_filtering": "🔍 After filtering: {count} URLs match\n",
        "invalid_filter": "⚠️ Invalid URL filter: {error}\n",
        "excluded_patterns": "🚫 Excluded {count} URLs matching patterns\n",
        "excluded_specific": "🚫 Excluded {count} specific URLs\n",
        "start_index_exceeds": "⚠️ start_from_index ({index}) exceeds URL count ({count})\n",
        "resuming_from": "⏭️ Resuming from index {index}, {count} URLs remaining\n",
        "limited_to": "📌 Limited to {count} URLs\n",
        "found_existing": "📚 Found {count} existing documents in KB\n",
        "building_cache": "🔗 Building URL cache for existing documents...\n",
        "mapped_docs": "🔗 Mapped {count} documents by URL\n",
        "unextractable_warning": "⚠️ {count} documents have unextractable URLs (need manual review)\n",
        "checking_stale": "🧹 Checking for stale documents...\n",
        "cleanup_skipped": "⚠️ Cleanup skipped: would delete {would_delete} of {total} docs (>{threshold}%)\n",
        "cleanup_skipped_empty_sitemap": "🛡️ Cleanup skipped: sitemap appears empty (safety protection)\n",
        "cleanup_skipped_too_few_docs": "🛡️ Cleanup skipped: too few documents in KB (safety protection)\n",
        "cleanup_skipped_max_limit": "⚠️ Cleanup skipped: would delete {would_delete} docs (exceeds max_cleanup_count of {max_count})\n",
        "cleanup_dry_run": "🔍 DRY RUN: Would delete {count} stale documents\n",
        "deleted_stale": "🗑️ Deleted {count} stale documents\n",
        "no_stale_found": "✨ No stale documents found\n",
        "status_created": "Created",
        "status_updated": "Updated",
        "status_skipped": "Skipped",
        "status_unchanged": "Unchanged",
        "status_failed": "Failed",
        "status_would_create": "[DRY RUN] Would create",
        "status_would_update": "[DRY RUN] Would update",
        "sync_completed": "\n\n✅ Sync completed!\n\n",
        "dry_run_completed": "\n\n🔍 DRY RUN completed! No changes were made.\n\n",
        "summary_processed": "📈 Processed: {processed}/{total}\n",
        "summary_created": "✅ Created: {count}\n",
        "summary_updated": "🔄 Updated: {count}\n",
        "summary_skipped": "⏭️ Skipped: {count}\n",
        "summary_unchanged": "✓ Unchanged: {count}\n",
        "summary_duplicates": "🔁 Duplicates: {count}\n",
        "summary_cleaned": "🗑️ Cleaned: {count}\n",
        "summary_failed": "❌ Failed: {count}\n",
        "summary_would_create": "✅ Would create: {count}\n",
        "summary_would_update": "🔄 Would update: {count}\n",
        "summary_would_clean": "🗑️ Would clean: {count}\n",
        "error_required_fields": "Error: dataset_id is required and at least one of sitemap_url or manual_urls must be provided",
        "failed_urls_header": "\n❌ Failed URLs:\n",
        "manual_review_header": "\n⚠️ Documents needing manual review ({count}):\n",
        "lastmod_enabled": "⚡ Lastmod optimization enabled (faster sync for unchanged content)\n",
        "lastmod_skipped": "⚡ Skipped (lastmod unchanged)",
        "summary_lastmod_skipped": "⚡ Lastmod skipped: {count}\n",
        # Incremental sync messages
        "incremental_mode": "⚡⚡ Incremental sync mode enabled\n",
        "incremental_storage": "💾 Manifest storage: {path}\n",
        "manifest_loaded": "📋 Loaded manifest from last sync ({timestamp})\n",
        "manifest_not_found": "📋 No manifest found, performing full sync (will be faster next time)\n",
        "manifest_invalid": "⚠️ Manifest invalid or corrupted, performing full sync\n",
        "manifest_filter_changed": "⚠️ Filter parameters changed since last sync, performing full sync\n",
        "force_full_sync": "🔄 Force full sync requested, ignoring manifest\n",
        "incremental_diff": "📊 Sitemap changes detected:\n   • {new} new URLs to add\n   • {modified} modified URLs to update\n   • {removed} URLs removed\n   • {unchanged} URLs unchanged (skipping)\n",
        "incremental_skipped": "⚡⚡ Skipped (unchanged in manifest)",
        "progress": "⚡⚡ [{current}/{total}] {action}: {title}\n",
        "manifest_saved": "💾 Manifest saved: {path}\n",
        "manifest_save_failed": "⚠️ Failed to save manifest: {error}\n",
        "summary_manifest_skipped": "⚡⚡ Manifest skipped: {count}\n",
        "estimated_time": "⏱️ Estimated time: ~{minutes} min (vs ~{full_minutes} min for full sync)\n",
    },
    "fr": {
        "starting_sync": "🚀 Démarrage de la synchronisation depuis :\n{url}\n",
        "starting_sync_manual": "🚀 Démarrage de la synchronisation depuis la liste manuelle ({count} URLs)\n",
        "starting_sync_both": "🚀 Démarrage de la synchronisation depuis sitemap + URLs manuelles ({count} URLs au total)\n",
        "dry_run_mode": "🔍 MODE SIMULATION : Aucune modification ne sera effectuée\n",
        "no_urls_found": "❌ Aucune URL trouvée dans le sitemap\n",
        "found_urls": "📋 {count} URLs trouvées dans le sitemap\n",
        "after_filtering": "🔍 Après filtrage : {count} URLs correspondent\n",
        "invalid_filter": "⚠️ Filtre URL invalide : {error}\n",
        "excluded_patterns": "🚫 {count} URLs exclues selon les motifs\n",
        "excluded_specific": "🚫 {count} URLs spécifiques exclues\n",
        "start_index_exceeds": "⚠️ start_from_index ({index}) dépasse le nombre d'URLs ({count})\n",
        "resuming_from": "⏭️ Reprise à l'index {index}, {count} URLs restantes\n",
        "limited_to": "📌 Limité à {count} URLs\n",
        "found_existing": "📚 {count} documents existants trouvés dans la KB\n",
        "building_cache": "🔗 Construction du cache des URLs des documents existants...\n",
        "mapped_docs": "🔗 {count} documents mappés par URL\n",
        "unextractable_warning": "⚠️ {count} documents ont des URLs non extractibles (révision manuelle nécessaire)\n",
        "checking_stale": "🧹 Recherche des documents obsolètes...\n",
        "cleanup_skipped": "⚠️ Nettoyage ignoré : supprimerait {would_delete} sur {total} docs (>{threshold}%)\n",
        "cleanup_skipped_empty_sitemap": "🛡️ Nettoyage ignoré : sitemap vide (protection de sécurité)\n",
        "cleanup_skipped_too_few_docs": "🛡️ Nettoyage ignoré : trop peu de documents (protection de sécurité)\n",
        "cleanup_skipped_max_limit": "⚠️ Nettoyage ignoré : supprimerait {would_delete} docs (dépasse max_cleanup_count de {max_count})\n",
        "cleanup_dry_run": "🔍 SIMULATION : Supprimerait {count} documents obsolètes\n",
        "deleted_stale": "🗑️ {count} documents obsolètes supprimés\n",
        "no_stale_found": "✨ Aucun document obsolète trouvé\n",
        "status_created": "Créé",
        "status_updated": "Mis à jour",
        "status_skipped": "Ignoré",
        "status_unchanged": "Inchangé",
        "status_failed": "Échec",
        "status_would_create": "[SIMULATION] Créerait",
        "status_would_update": "[SIMULATION] Mettrait à jour",
        "sync_completed": "\n\n✅ Synchronisation terminée !\n\n",
        "dry_run_completed": "\n\n🔍 SIMULATION terminée ! Aucune modification effectuée.\n\n",
        "summary_processed": "📈 Traités : {processed}/{total}\n",
        "summary_created": "✅ Créés : {count}\n",
        "summary_updated": "🔄 Mis à jour : {count}\n",
        "summary_skipped": "⏭️ Ignorés : {count}\n",
        "summary_unchanged": "✓ Inchangés : {count}\n",
        "summary_duplicates": "🔁 Doublons : {count}\n",
        "summary_cleaned": "🗑️ Nettoyés : {count}\n",
        "summary_failed": "❌ Échoués : {count}\n",
        "summary_would_create": "✅ Créerait : {count}\n",
        "summary_would_update": "🔄 Mettrait à jour : {count}\n",
        "summary_would_clean": "🗑️ Nettoierait : {count}\n",
        "error_required_fields": "Erreur : dataset_id est requis et au moins un des champs sitemap_url ou manual_urls doit être fourni",
        "failed_urls_header": "\n❌ URLs en échec :\n",
        "manual_review_header": "\n⚠️ Documents nécessitant une révision manuelle ({count}) :\n",
        "lastmod_enabled": "⚡ Optimisation lastmod activée (sync plus rapide pour le contenu inchangé)\n",
        "lastmod_skipped": "⚡ Ignoré (lastmod inchangé)",
        "summary_lastmod_skipped": "⚡ Ignorés par lastmod : {count}\n",
        # Incremental sync messages
        "incremental_mode": "⚡⚡ Mode synchronisation incrémentale activé\n",
        "incremental_storage": "💾 Stockage du manifest : {path}\n",
        "manifest_loaded": "📋 Manifest chargé depuis la dernière sync ({timestamp})\n",
        "manifest_not_found": "📋 Manifest non trouvé, synchronisation complète (plus rapide la prochaine fois)\n",
        "manifest_invalid": "⚠️ Manifest invalide ou corrompu, synchronisation complète\n",
        "manifest_filter_changed": "⚠️ Paramètres de filtre modifiés, synchronisation complète\n",
        "force_full_sync": "🔄 Synchronisation complète forcée, manifest ignoré\n",
        "incremental_diff": "📊 Changements détectés :\n   • {new} nouvelles URLs à ajouter\n   • {modified} URLs modifiées à mettre à jour\n   • {removed} URLs supprimées\n   • {unchanged} URLs inchangées (ignorées)\n",
        "incremental_skipped": "⚡⚡ Ignoré (inchangé dans le manifest)",
        "progress": "⚡⚡ [{current}/{total}] {action} : {title}\n",
        "manifest_saved": "💾 Manifest sauvegardé : {path}\n",
        "manifest_save_failed": "⚠️ Échec de sauvegarde du manifest : {error}\n",
        "summary_manifest_skipped": "⚡⚡ Ignorés par manifest : {count}\n",
        "estimated_time": "⏱️ Temps estimé : ~{minutes} min (vs ~{full_minutes} min pour sync complète)\n",
    },
}


def get_message(lang: str, key: str, **kwargs: Any) -> str:
    """Get a localized message by key with optional formatting.

    Args:
        lang: Language code ('en' or 'fr')
        key: Message key to look up
        **kwargs: Optional format arguments for the message template

    Returns:
        Formatted message string, falls back to English if key not found
    """
    messages = MESSAGES.get(lang, MESSAGES["en"])
    template = messages.get(key) or MESSAGES["en"].get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except KeyError:
            return template
    return template

