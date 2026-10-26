import { useState } from 'react';

export function BrokenCard({ visible }: { visible: boolean }) {
  if (visible) {
    const [name] = useState('Granite');
    return <article>{name}</article>;
  }
  return null;
}
