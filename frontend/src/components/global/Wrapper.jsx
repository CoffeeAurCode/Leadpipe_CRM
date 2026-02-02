import { cn } from "@/lib";

const Wrapper = ({ className, children }) => {
    return (
        <section
            className={cn(
                "h-full mx-auto w-full max-w-7xl px-4 lg:px-8",
                className
            )}
        >
            {children}
        </section>
    );
};

export default Wrapper;
