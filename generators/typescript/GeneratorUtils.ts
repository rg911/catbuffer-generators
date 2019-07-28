/**
 * Generator utility class.
 */
export class GeneratorUtils {

	/**
     * Converts a (64bit) uint8 array into a number array.
     * @param {Uint8Array} input A uint8 array.
     * @returns {number[]} The uint64 representation of the input.
     */
    public static uint64FromBytes (input: Uint8Array): number[] {
        if (8 !== input.length) {
            throw Error(`byte array has unexpected size '${input.length}'`);
        }
        return [GeneratorUtils.readUint32At(input, 0), GeneratorUtils.readUint32At(input, 4)];
	}
	
	/**
     * Read buffer into 32bits integer at given index.
     * @param {Uint8Array} bytes A uint8 array.
	 * @param {number} index Index.
     * @returns {number} 32bits integer.
     */
	public static readUint32At(bytes: Uint8Array, index: number): number {
		return (bytes[index] + (bytes[index + 1] << 8) + (bytes[index + 2] << 16) + (bytes[index + 3] << 24)) >>> 0;
	}

	/**
     * Write uint to buffer
     * @param {number} uintValue A uint8 array.
	 * @param {number} bufferSize Buffer size.
     * @returns {Uint8Array}
     */
	public static uintToBuffer (uintValue: number, bufferSize: number): Uint8Array {
		const buffer = new ArrayBuffer(bufferSize);
		const dataView = new DataView(buffer);
		if (1 === bufferSize)
			dataView.setUint8(0, uintValue);
	
		else if (2 === bufferSize)
			dataView.setUint16(0, uintValue, true);
	
		else if (4 === bufferSize)
			dataView.setUint32(0, uintValue, true);
	
		else
			throw new Error('Unexpected bufferSize');
	
		return new Uint8Array(buffer);
	};

	/**
     * Write Uint64 to buffer
     * @param {number} uintValue Uint64 (number[]).
     * @returns {Uint8Array}
     */
	public static uint64ToBuffer(uintValue: number[]): Uint8Array {
		const uint32Array = new Uint32Array(uintValue);
		return new Uint8Array(uint32Array.buffer).reverse();
	}

	/**
     * Concatenate two arrays
     * @param {Uint8Array} array1 A Uint8Array.
	 * @param {Uint8Array} array2 A Uint8Array.
     * @returns {Uint8Array}
     */
	public static concatTypedArrays(array1: Uint8Array, array2: Uint8Array): Uint8Array {
		const newArray = new Uint8Array(array1.length + array2.length);
		newArray.set(array1);
		newArray.set(array2, array1.length);
		return newArray;
	};

	/**
     * Genreate fixed size array
     * @param {Uint8Array} array A Uint8Array.
	 * @param {number} size Array size.
     * @returns {Uint8Array}
     */
	public static fitByteArray (array: Uint8Array, size: number): Uint8Array {
		if (array.length > size) {
			throw new RangeError('Data size larger than allowed');
		} else if (array.length < size) {
			const newArray = new Uint8Array(size);
			newArray.fill(0);
			newArray.set(array, size - array.length);
			return newArray;
		}
		return array;
	};
}
