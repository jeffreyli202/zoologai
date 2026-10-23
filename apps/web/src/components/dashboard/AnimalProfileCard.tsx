import type { Animal } from "@/lib/types";

type AnimalProfileCardProps = {
  animal: Animal;
  featured?: boolean;
};

/**
 * Props example: the parent passes an `animal` object in.
 * This component does not fetch data — it only renders what it receives.
 */
export function AnimalProfileCard({
  animal,
  featured = false,
}: AnimalProfileCardProps) {
  return (
    <article
      className={`rounded-2xl border border-border bg-surface p-5 shadow-[0_1px_0_rgba(45,61,50,0.04)] ${
        featured ? "md:p-6" : ""
      }`}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-sage-500">
        Animal profile
      </p>
      <h3 className="mt-2 font-display text-2xl text-sage-900">{animal.name}</h3>
      <p className="mt-1 text-sm italic text-muted">{animal.species}</p>
      {animal.description ? (
        <p className="mt-3 text-sm leading-6 text-ink/80">{animal.description}</p>
      ) : (
        <p className="mt-3 text-sm text-muted">No description yet.</p>
      )}
    </article>
  );
}
