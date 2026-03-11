import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function TrendsChart({ data }) {
    return (
        <div className="bg-card border border-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-foreground mb-4">Complaints Over Time</h3>
            <ResponsiveContainer width="100%" height={200}>
                <LineChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--chart-grid))" />
                    <XAxis
                        dataKey="date"
                        tick={{ fill: 'hsl(var(--chart-text))', fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                    />
                    <YAxis
                        tick={{ fill: 'hsl(var(--chart-text))', fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        allowDecimals={false}
                    />
                    <Tooltip
                        contentStyle={{
                            background: 'hsl(var(--card))',
                            border: '1px solid hsl(var(--border))',
                            borderRadius: '8px',
                            color: 'hsl(var(--foreground))',
                            fontSize: 12,
                        }}
                        cursor={{ stroke: 'hsl(var(--chart-grid))' }}
                    />
                    <Line
                        type="monotone"
                        dataKey="complaints"
                        stroke="hsl(var(--chart-1))"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4, fill: 'hsl(var(--chart-1))' }}
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}
