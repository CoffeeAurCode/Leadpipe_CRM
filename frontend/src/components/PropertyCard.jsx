import { Bed, Bath, MapPin, CheckCircle2, XCircle } from 'lucide-react';
import { cn } from '@/lib';

function PropertyCard({ property, onClick }) {
    return (
        <div
            className={cn(
                "bg-card border border-border rounded-lg overflow-hidden",
                "hover:border-primary hover:shadow-lg hover:shadow-primary/10",
                "transition-all duration-300 group cursor-pointer"
            )}
            onClick={() => onClick?.(property)}
        >
            {/* Property Image */}
            <div className="relative h-48 overflow-hidden">
                <img
                    src={property.image_url || "/placeholder.jpg"}
                    alt={property.name}
                    className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
                    onError={(e) => { e.target.src = "/placeholder.jpg"; }}
                />
                {/* Occupancy Badge */}
                <div className="absolute top-3 right-3">
                    {!!property.tenant_uuid ? (
                        <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-red-500/90 text-white text-xs font-medium">
                            <XCircle className="w-3 h-3" />
                            <span>Occupied</span>
                        </div>
                    ) : (
                        <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-green-500/90 text-white text-xs font-medium">
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Available</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Property Details */}
            <div className="p-4 space-y-3">
                {/* Title */}
                <div>
                    <h3 className="text-lg font-semibold text-foreground group-hover:text-primary transition-colors line-clamp-1">
                        {property.name}
                    </h3>
                    <div className="flex items-center gap-1 text-sm text-muted-foreground mt-1">
                        <MapPin className="w-3.5 h-3.5" />
                        <span className="line-clamp-1">{property.address}</span>
                    </div>
                </div>

                {/* Features */}
                <div className="flex items-center gap-4 pt-2 border-t border-border">
                    <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                        <Bed className="w-4 h-4 text-primary" />
                        <span className="font-medium text-foreground">{property.bedrooms}</span>
                        <span>Bed{property.bedrooms !== 1 ? 's' : ''}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                        <Bath className="w-4 h-4 text-primary" />
                        <span className="font-medium text-foreground">{property.bathrooms}</span>
                        <span>Bath{property.bathrooms !== 1 ? 's' : ''}</span>
                    </div>
                </div>

                {/* Flat Number Badge */}
                <div className="pt-2">
                    <span className="inline-block px-2 py-1 text-xs font-medium rounded-md bg-secondary text-foreground">
                        Unit #{property.flat_number}
                    </span>
                </div>
            </div>
        </div>
    );
}

export default PropertyCard;
