import type { Entity } from './types';

/** Short label only in the card; full source label stays in the hierarchy context. */
export function entityCardTitle(entity: Entity | undefined, fallback: string): string {
  if (!entity) return fallback;
  return entity.entity_label
    .replace(/^\d+(?:\.\d+)*\.\s*/, '')
    .replace(/\s+-\s+ghi nhận trên hệ thống$/i, '');
}

/** Walk parent IDs instead of assuming a fixed Project → Section → Item depth. */
export function entityTrail(entities: Entity[], entityId: string): Entity[] {
  const lookup = new Map(entities.map(entity => [entity.entity_id, entity]));
  const trail: Entity[] = [];
  const seen = new Set<string>();
  let current = lookup.get(entityId);
  while (current && !seen.has(current.entity_id)) {
    trail.unshift(current);
    seen.add(current.entity_id);
    current = current.parent_entity_id ? lookup.get(current.parent_entity_id) : undefined;
  }
  return trail;
}
