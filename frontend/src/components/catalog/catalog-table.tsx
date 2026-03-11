'use client';

import { useState, useEffect, useCallback, useTransition } from 'react';
import { Search, ChevronLeft, ChevronRight, Pencil, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from '@/components/ui/table';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import { getCatalogProducts, saveProductOverride } from '@/lib/actions/catalog-actions';
import { ProductEditDialog } from './product-edit-dialog';

interface ProductData {
  row_index: number;
  category: string;
  summary: string;
  fields: Record<string, unknown>;
  kostentraeger?: string;
  hasOverride: boolean;
  overrideAction: string | null;
  overrideId: string | null;
}

interface CatalogTableProps {
  catalogId: string;
  initialProducts: ProductData[];
  initialTotal: number;
  initialPages: number;
  categories: string[];
  canEdit: boolean;
}

export function CatalogTable({
  catalogId,
  initialProducts,
  initialTotal,
  initialPages,
  categories,
  canEdit,
}: CatalogTableProps) {
  const [products, setProducts] = useState<ProductData[]>(initialProducts);
  const [total, setTotal] = useState(initialTotal);
  const [pages, setPages] = useState(initialPages);
  const [currentPage, setCurrentPage] = useState(1);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<string>('');
  const [isPending, startTransition] = useTransition();
  const [editProduct, setEditProduct] = useState<ProductData | null>(null);
  const [editMode, setEditMode] = useState<'add' | 'edit'>('edit');
  const [showEditDialog, setShowEditDialog] = useState(false);

  const fetchProducts = useCallback(
    (searchVal: string, categoryVal: string, page: number) => {
      startTransition(async () => {
        const result = await getCatalogProducts(
          catalogId,
          searchVal || undefined,
          categoryVal || undefined,
          page
        );
        if ('error' in result) {
          toast.error(result.error as string);
          return;
        }
        setProducts(result.products as ProductData[]);
        setTotal(result.total);
        setPages(result.pages);
      });
    },
    [catalogId]
  );

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      setCurrentPage(1);
      fetchProducts(search, category, 1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search, category, fetchProducts]);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    fetchProducts(search, category, page);
  };

  const handleEdit = (product: ProductData) => {
    setEditProduct(product);
    setEditMode('edit');
    setShowEditDialog(true);
  };

  const handleAdd = () => {
    setEditProduct(null);
    setEditMode('add');
    setShowEditDialog(true);
  };

  const handleDelete = async (product: ProductData) => {
    const key = product.kostentraeger || String(product.row_index);
    if (!confirm(`Produkt "${key}" wirklich loeschen?`)) return;

    try {
      await saveProductOverride(catalogId, key, 'delete');
      toast.success('Produkt als geloescht markiert');
      fetchProducts(search, category, currentPage);
    } catch {
      toast.error('Fehler beim Loeschen');
    }
  };

  const handleDialogClose = () => {
    setShowEditDialog(false);
    setEditProduct(null);
    fetchProducts(search, category, currentPage);
  };

  return (
    <div className="space-y-4" data-testid="catalog-table">
      {/* Search and filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Produkte suchen..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            data-testid="search-input"
          />
        </div>
        <Select
          value={category}
          onValueChange={(val: string | null) => setCategory(val ?? '')}
        >
          <SelectTrigger data-testid="category-filter">
            <SelectValue placeholder="Alle Kategorien" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Alle Kategorien</SelectItem>
            {categories.map((cat) => (
              <SelectItem key={cat} value={cat}>
                {cat}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {canEdit && (
          <Button size="sm" onClick={handleAdd} data-testid="add-product-btn">
            Produkt hinzufuegen
          </Button>
        )}
      </div>

      {/* Loading indicator */}
      {isPending && (
        <div className="text-sm text-muted-foreground" data-testid="loading-indicator">
          Laden...
        </div>
      )}

      {/* Product table */}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Kategorie</TableHead>
            <TableHead>Kostentraeger</TableHead>
            <TableHead>Tuertyp</TableHead>
            <TableHead>Brandschutz</TableHead>
            <TableHead>Masse</TableHead>
            {canEdit && <TableHead className="text-right">Aktionen</TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {products.length === 0 ? (
            <TableRow>
              <TableCell colSpan={canEdit ? 6 : 5} className="text-center py-8 text-muted-foreground">
                Keine Produkte gefunden
              </TableCell>
            </TableRow>
          ) : (
            products.map((product) => {
              const fields = product.fields || {};
              return (
                <TableRow key={product.row_index} data-testid={`product-row-${product.row_index}`}>
                  <TableCell>{product.category}</TableCell>
                  <TableCell>
                    <span className="flex items-center gap-1.5">
                      {product.kostentraeger || String(product.row_index)}
                      {product.hasOverride && (
                        <Badge variant="secondary" className="text-xs" data-testid="override-badge">
                          Bearbeitet
                        </Badge>
                      )}
                    </span>
                  </TableCell>
                  <TableCell>{String(fields.tuertyp ?? '-')}</TableCell>
                  <TableCell>{String(fields.brandschutz ?? '-')}</TableCell>
                  <TableCell>{String(fields.masse ?? '-')}</TableCell>
                  {canEdit && (
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => handleEdit(product)}
                          data-testid={`edit-btn-${product.row_index}`}
                        >
                          <Pencil className="size-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => handleDelete(product)}
                          data-testid={`delete-btn-${product.row_index}`}
                        >
                          <Trash2 className="size-3.5 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              );
            })
          )}
        </TableBody>
      </Table>

      {/* Pagination */}
      <div className="flex items-center justify-between text-sm" data-testid="pagination">
        <span className="text-muted-foreground">
          {total} Produkte gesamt, Seite {currentPage} von {pages || 1}
        </span>
        <div className="flex gap-1">
          <Button
            variant="outline"
            size="sm"
            disabled={currentPage <= 1}
            onClick={() => handlePageChange(currentPage - 1)}
            data-testid="prev-page"
          >
            <ChevronLeft className="size-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={currentPage >= pages}
            onClick={() => handlePageChange(currentPage + 1)}
            data-testid="next-page"
          >
            <ChevronRight className="size-4" />
          </Button>
        </div>
      </div>

      {/* Edit dialog */}
      {showEditDialog && (
        <ProductEditDialog
          catalogId={catalogId}
          product={editMode === 'edit' ? editProduct ?? undefined : undefined}
          mode={editMode}
          onClose={handleDialogClose}
        />
      )}
    </div>
  );
}
