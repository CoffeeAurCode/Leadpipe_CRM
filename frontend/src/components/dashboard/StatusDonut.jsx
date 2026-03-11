import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const COLORS = [
    'hsl(var(--chart-4))', // Pending — amber
    'hsl(var(--chart-2))', // In Progress — blue
    'hsl(var(--chart-3))', // Resolved — green
];

export default function StatusDonut({ data }) {
    const total = data.reduce((s, d) => s + d.value, 0);

    return (
        <div className="bg-card border border-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-foreground mb-1">Status Breakdown</h3>
            {total === 0 ? (
                <div className="flex items-center justify-center h-[200px] text-sm text-muted-foreground">
                    No data for this period
                </div>
            ) : (
                <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                        <Pie
                            data={data}
                            cx="50%"
                            cy="50%"
                            innerRadius={55}
                            outerRadius={80}
                            paddingAngle={3}
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
                                <span style={{ color: 'hsl(var(--muted-foreground))', fontSize: 12 }}>
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
