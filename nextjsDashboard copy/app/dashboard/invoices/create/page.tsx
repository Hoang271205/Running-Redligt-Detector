import Form from '@/app/ui/invoices/create-form';
import Breadcrumbs from '@/app/ui/invoices/breadcrumbs';
import { fetchCustomers } from '@/app/lib/data';
import { Metadata } from 'next';
export const metadata: Metadata = {
    title: 'Create Invoice',
    description: 'Create a new invoice in the Acme Dashboard',
    openGraph: {
        title: 'Create Invoice',
        description: 'Create a new invoice in the Acme Dashboard',
        images: [
            {
                url: '/public/Test.ico',
                width: 1200,
                height: 630,
                alt: 'Create Invoice Banner',
            },
        ],
    },
};

export default async function Page() {
    const customers = await fetchCustomers();

    return (
        <main>
            <Breadcrumbs
                breadcrumbs={[
                    { label: 'Invoices', href: '/dashboard/invoices' },
                    {
                        label: 'Create Invoice',
                        href: '/dashboard/invoices/create',
                        active: true,
                    },
                ]}
            />
            <Form customers={customers} />
        </main>
    );
}