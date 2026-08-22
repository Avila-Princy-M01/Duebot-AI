import { InvoiceTable } from "../../components/invoices/InvoiceTable";
import { listInvoices } from "../../lib/api";

export async function InvoicesPage() {
  const payload = await listInvoices();
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Invoices</h1>
      <InvoiceTable invoices={payload.data} />
    </div>
  );
}

export default InvoicesPage;
