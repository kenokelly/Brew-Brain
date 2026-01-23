'use client';

import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';

interface SocketContextValue {
    socket: Socket | null;
    isConnected: boolean;
    connectionError: string | null;
}

const SocketContext = createContext<SocketContextValue>({
    socket: null,
    isConnected: false,
    connectionError: null,
});

export const useSocket = () => {
    return useContext(SocketContext);
};

export const SocketProvider = ({ children }: { children: React.ReactNode }) => {
    const [socket, setSocket] = useState<Socket | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [connectionError, setConnectionError] = useState<string | null>(null);

    useEffect(() => {
        // Connect to the API server with robust reconnection settings
        const newSocket = io({
            path: '/socket.io',
            // Reconnection settings with exponential backoff
            reconnection: true,
            reconnectionAttempts: Infinity, // Keep trying indefinitely
            reconnectionDelay: 1000, // Start with 1 second delay
            reconnectionDelayMax: 10000, // Cap at 10 seconds
            randomizationFactor: 0.5, // Add randomness to prevent thundering herd
            // Connection settings
            timeout: 20000, // 20 second timeout for initial connection
            transports: ['websocket', 'polling'], // Prefer WebSocket, fallback to polling
            autoConnect: true,
        });

        // Connection event handlers
        newSocket.on('connect', () => {
            console.log('[Socket] Connected:', newSocket.id);
            setIsConnected(true);
            setConnectionError(null);
        });

        newSocket.on('disconnect', (reason) => {
            console.log('[Socket] Disconnected:', reason);
            setIsConnected(false);
            // Only set error for unexpected disconnects
            if (reason === 'io server disconnect' || reason === 'io client disconnect') {
                // Intentional disconnect, no error
            } else {
                setConnectionError(`Disconnected: ${reason}`);
            }
        });

        newSocket.on('connect_error', (error) => {
            console.error('[Socket] Connection error:', error.message);
            setConnectionError(error.message);
            setIsConnected(false);
        });

        newSocket.on('reconnect', (attemptNumber) => {
            console.log('[Socket] Reconnected after', attemptNumber, 'attempts');
            setIsConnected(true);
            setConnectionError(null);
        });

        newSocket.on('reconnect_attempt', (attemptNumber) => {
            console.log('[Socket] Reconnection attempt', attemptNumber);
        });

        newSocket.on('reconnect_error', (error) => {
            console.error('[Socket] Reconnection error:', error.message);
        });

        newSocket.on('reconnect_failed', () => {
            console.error('[Socket] Reconnection failed after all attempts');
            setConnectionError('Failed to reconnect to server');
        });

        setSocket(newSocket);

        return () => {
            // Remove all listeners before closing
            newSocket.off('connect');
            newSocket.off('disconnect');
            newSocket.off('connect_error');
            newSocket.off('reconnect');
            newSocket.off('reconnect_attempt');
            newSocket.off('reconnect_error');
            newSocket.off('reconnect_failed');
            newSocket.close();
        };
    }, []);

    const value: SocketContextValue = {
        socket,
        isConnected,
        connectionError,
    };

    return (
        <SocketContext.Provider value={value}>
            {children}
        </SocketContext.Provider>
    );
};
