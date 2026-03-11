import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const COLORS = [
    'hsl(var(--chart-1))',
    'hsl(var(--chart-2))',
    'hsl(var(--chart-3))',
    'hsl(var(--chart-4))',
    'hsl(17 100% 70%)',
    'hsl(215 70% 70%)',
    'hsl(142 70% 65%)',
];

export default function CategoriesPie({ data }) {
    const total = data.reduce((s, d) => s + d.value, 0);

    return (
        <div className="bg-card border border-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-foreground mb-1">Complaint Categories</h3>
            {total === 0 ? (
                <div className="flex items-center justify-center h-[220px] text-sm text-muted-foreground">
                    No data for this period
                </div>
            ) : (
                <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                        <Pie
                            data={data}
                            cx="50%"
                            cy="45%"
                            outerRadius={75}
                            paddingAngle={2}
                            dataKey="value"
                            strokeWidth={0}
                        >
                            {data.map((_, i) => (
                                <Cell key={i} fill={COLORS[i % COLORS.length]} />
                            ))}
                        </Pie>
                        <Tooltip
                            contentStyle={{
                                background: 'hsl(var(--card))',
                                border: '1px solid hsl(var(--border))',
                                borderRadius: '8px',
                                color: 'hsl(var(--foreground))',
                                fontSize: 12,
                            }}
                        />
                        <Legend
                            iconSize={8}
                            formatter={(value) => (
                                <span style={{ color: 'hsl(var(--muted-foreground))', fontSize: 11 }}>
                                    {value}
                                </span>
                            )}
                        />
                    </PieChart>
                </ResponsiveContainer>
            )}
        </div>
    );
}
