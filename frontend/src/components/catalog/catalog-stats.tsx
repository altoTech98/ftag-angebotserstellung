'use client';

import { Package, Layers, Grid3X3, FolderTree } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

interface CatalogStatsProps {
  totalProducts: number;
  mainProducts: number;
  accessoryProducts: number;
  categories: number;
}

export function CatalogStats({
  totalProducts,
  mainProducts,
  accessoryProducts,
  categories,
}: CatalogStatsProps) {
  const stats = [
    {
      label: 'Produkte gesamt',
      value: totalProducts,
      icon: Package,
      testId: 'stat-total',
    },
    {
      label: 'Hauptprodukte',
      value: mainProducts,
      icon: Layers,
      testId: 'stat-main',
    },
    {
      label: 'Zubehoer',
      value: accessoryProducts,
      icon: Grid3X3,
      testId: 'stat-accessory',
    },
    {
      label: 'Kategorien',
      value: categories,
      icon: FolderTree,
      testId: 'stat-categories',
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4" data-testid="catalog-stats">
      {stats.map((stat) => (
        <Card key={stat.testId}>
          <CardContent className="flex items-center gap-3 pt-4">
            <stat.icon className="size-5 text-muted-foreground" />
            <div>
              <p
                className="text-2xl font-semibold"
                data-testid={stat.testId}
              >
                {stat.value}
              </p>
              <p className="text-xs text-muted-foreground">{stat.label}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
