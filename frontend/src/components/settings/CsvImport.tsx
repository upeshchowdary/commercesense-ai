import { useMutation } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, Download, Upload } from 'lucide-react'
import { useRef, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ApiError, getImportTemplate, postCommitCsv, postValidateCsv } from '@/lib/api'
import type { CsvImportResult, CsvValidationResult, ImportDataType } from '@/lib/types'

// Spec §25: a seller or judge must be able to get real data into all four
// intelligence modules without any Amazon API. Download Template -> Upload
// -> Validate -> Preview -> Import, wired straight to the existing
// api/routers/data_import.py endpoints (no new backend logic here).

const DATA_TYPES: { value: ImportDataType; label: string }[] = [
  { value: 'listing', label: 'Listing' },
  { value: 'pricing', label: 'Pricing' },
  { value: 'reviews', label: 'Reviews' },
  { value: 'inventory', label: 'Inventory' },
]

export function CsvImport() {
  const [dataType, setDataType] = useState<ImportDataType>('listing')
  const [file, setFile] = useState<File | null>(null)
  const [validation, setValidation] = useState<CsvValidationResult | null>(null)
  const [importResult, setImportResult] = useState<CsvImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const templateMutation = useMutation({
    mutationFn: () => getImportTemplate(dataType),
    onSuccess: (tpl) => {
      const blob = new Blob([tpl.csv_content], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = tpl.filename
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  const validateMutation = useMutation({
    mutationFn: (f: File) => postValidateCsv(dataType, f),
    onSuccess: (result) => {
      setValidation(result)
      setImportResult(null)
      setError(null)
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Validation failed.'),
  })

  const commitMutation = useMutation({
    mutationFn: (f: File) => postCommitCsv(dataType, f),
    onSuccess: (result) => {
      setImportResult(result)
      setValidation(null)
      setFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Import failed.'),
  })

  function resetForNewType(next: ImportDataType) {
    setDataType(next)
    setFile(null)
    setValidation(null)
    setImportResult(null)
    setError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        Bring your own listing, pricing, review, or inventory data in without any Amazon API — download a
        template, fill it in, then validate and import. No row is ever silently discarded.
      </p>

      <Tabs value={dataType} onValueChange={(v) => resetForNewType(v as ImportDataType)}>
        <TabsList>
          {DATA_TYPES.map((t) => (
            <TabsTrigger key={t.value} value={t.value}>
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => templateMutation.mutate()}
          disabled={templateMutation.isPending}
        >
          <Download className="size-4" />
          Download {dataType}_data.csv template
        </Button>

        <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-border px-3 py-2 text-xs font-medium text-foreground hover:bg-muted">
          <Upload className="size-4" />
          {file ? file.name : 'Choose CSV file'}
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null
              setFile(f)
              setValidation(null)
              setImportResult(null)
              setError(null)
            }}
          />
        </label>

        <Button
          size="sm"
          variant="secondary"
          disabled={!file || validateMutation.isPending}
          onClick={() => file && validateMutation.mutate(file)}
        >
          {validateMutation.isPending ? 'Validating…' : 'Validate'}
        </Button>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
          <AlertTriangle className="size-4" /> {error}
        </div>
      )}

      {validation && (
        <div className="flex flex-col gap-3 rounded-lg border border-border p-4">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Badge variant="outline">{validation.total_rows} rows</Badge>
            <Badge variant="live">{validation.valid_count} valid</Badge>
            {validation.invalid_count > 0 && <Badge variant="danger">{validation.invalid_count} invalid</Badge>}
          </div>

          {validation.invalid_rows.length > 0 && (
            <div className="max-h-64 overflow-y-auto rounded-md border border-border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Row</TableHead>
                    <TableHead>Errors</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {validation.invalid_rows.map((r) => (
                    <TableRow key={r.row}>
                      <TableCell className="font-mono text-xs">{r.row}</TableCell>
                      <TableCell className="text-xs text-danger">{r.errors.join('; ')}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          <div>
            <Button
              size="sm"
              disabled={validation.valid_count === 0 || !file || commitMutation.isPending}
              onClick={() => file && commitMutation.mutate(file)}
            >
              {commitMutation.isPending ? 'Importing…' : `Import ${validation.valid_count} valid row(s)`}
            </Button>
            {validation.valid_count === 0 && (
              <p className="mt-1 text-xs text-muted-foreground">
                Fix the errors above and re-validate — nothing to import yet.
              </p>
            )}
          </div>
        </div>
      )}

      {importResult && (
        <div className="flex items-center gap-2 rounded-md border border-success/40 bg-success/10 px-3 py-2 text-sm text-success">
          <CheckCircle2 className="size-4" />
          Imported {importResult.imported} row(s){importResult.skipped > 0 && `, skipped ${importResult.skipped} invalid`}.
        </div>
      )}
    </div>
  )
}
