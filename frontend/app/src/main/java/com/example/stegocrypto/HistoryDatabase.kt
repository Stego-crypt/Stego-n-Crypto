package com.example.stegocrypto

import android.content.Context
import androidx.room.*
import kotlinx.coroutines.flow.Flow

// ==========================================
// 1. THE ENTITY (Database Table Structure)
// ==========================================
@Entity(tableName = "scan_history")
data class ScanRecord(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val filename: String,
    val status: String,
    val authority: String,
    val timestamp: String
)

// ==========================================
// 2. THE DAO (Data Access Object / Queries)
// ==========================================
@Dao
interface ScanHistoryDao {

    // We use 'Flow' here. This is magic: it creates a live pipeline to the UI.
    // If a new scan is added to the database, the UI updates instantly and automatically.
    @Query("SELECT * FROM scan_history ORDER BY id DESC")
    fun getAllHistory(): Flow<List<ScanRecord>>

    // REMOVED 'suspend' and ': Long' to bypass the Kotlin KSP compiler bug!
    // We will manually put this on a background thread over in MainActivity.
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    fun insertRecord(record: ScanRecord)
}

// ==========================================
// 3. THE DATABASE ENGINE
// ==========================================
@Database(entities = [ScanRecord::class], version = 1, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {

    abstract fun scanHistoryDao(): ScanHistoryDao

    companion object {
        // @Volatile ensures that changes to INSTANCE are immediately visible to all threads
        @Volatile private var INSTANCE: AppDatabase? = null

        // This is a "Singleton". It ensures we only ever open ONE connection to the database
        // to prevent memory leaks and database locks.
        fun getDatabase(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "stegocrypto_database"
                ).build()
                INSTANCE = instance
                instance
            }
        }
    }
}